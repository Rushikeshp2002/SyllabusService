"""
Gemini PDF extraction service.

Handles:
  - PDF upload to Gemini Files API (with timeout + cleanup-on-error)
  - Schema conversion (Pydantic v2 → Gemini-safe flat JSON Schema)
  - Two-pass extraction (TOC → Full hierarchy)
  - Descriptive mode: per-chapter extraction (one API call per chapter)
  - Model fallback: rotates across models when daily RPD quota is exhausted
  - 429 rate-limit retry with exponential backoff (for RPM limits)
  - JSON truncation repair (EOF mid-object recovery)
"""

import re
import time
import logging

import google.generativeai as genai

from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_FALLBACK_MODELS
from models import TOCExtraction, TextbookExtraction, Chapter, ExtractionMetadata, SingleChapterExtraction, ChapterQuestions
from prompt import build_toc_prompt, build_extraction_prompt, build_single_chapter_prompt, build_question_extraction_prompt
from json_repair_util import repair_truncated_json

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)

FILE_PROCESSING_TIMEOUT = 120   # seconds
MAX_OUTPUT_TOKENS = 65536       # Gemini 2.5 Flash supports up to 65536
MAX_CONTINUATION_ATTEMPTS = 3
RPM_RETRY_WAIT = 35             # seconds to wait on RPM (per-minute) rate limit



# ── Schema conversion ─────────────────────────────────────────────────────────

_UNSUPPORTED_KEYS = frozenset({
    "$defs", "$ref", "$schema", "title",
    "default", "examples", "discriminator",
})


def _to_gemini_schema(pydantic_cls) -> dict:
    """Convert a Pydantic v2 model to a Gemini-compatible JSON Schema dict."""
    raw_schema = pydantic_cls.model_json_schema()
    defs = raw_schema.get("$defs", {})

    _resolving: set[str] = set()  # tracks refs currently being resolved (cycle detection)

    def _resolve_refs(node, depth=0):
        if depth > 10:
            return node  # safety limit
        if not isinstance(node, dict):
            return [_resolve_refs(i, depth) for i in node] if isinstance(node, list) else node
        if "$ref" in node:
            ref_name = node["$ref"].rsplit("/", 1)[-1]
            if ref_name in _resolving:
                # Circular reference — return the ref unresolved (will be stripped later)
                return defs.get(ref_name, node)
            if ref_name in defs:
                _resolving.add(ref_name)
                result = _resolve_refs(defs[ref_name], depth + 1)
                _resolving.discard(ref_name)
                return result
            return node
        return {k: _resolve_refs(v, depth) for k, v in node.items()}

    def _handle_any_of(node):
        if not isinstance(node, dict):
            return [_handle_any_of(i) for i in node] if isinstance(node, list) else node
        result = {}
        for k, v in node.items():
            if k == "anyOf" and isinstance(v, list):
                non_null = [o for o in v if not (isinstance(o, dict) and o.get("type") == "null")]
                if len(non_null) == 1:
                    merged = _handle_any_of(non_null[0])
                    merged["nullable"] = True
                    result.update(merged)
                else:
                    result[k] = _handle_any_of(v)
            else:
                result[k] = _handle_any_of(v)
        return result

    def _strip_unsupported(node):
        if isinstance(node, dict):
            return {
                k: _strip_unsupported(v)
                for k, v in node.items()
                if k not in _UNSUPPORTED_KEYS
                # Strip "description" only when it's a schema annotation (string),
                # keep it when it's a model property definition (dict)
                and not (k == "description" and isinstance(v, str))
            }
        if isinstance(node, list):
            return [_strip_unsupported(i) for i in node]
        return node

    return _strip_unsupported(_handle_any_of(_resolve_refs(raw_schema)))


# ── Model rotation + rate-limit handling ──────────────────────────────────────

# Tracks which models have exhausted their daily RPD quota
_exhausted_models: set[str] = set()


def _is_daily_quota_error(error_str: str) -> bool:
    """Check if a 429 error is a DAILY quota exhaustion (not just RPM)."""
    return "PerDay" in error_str or "daily" in error_str.lower()


def _get_available_model() -> str | None:
    """Get the first non-exhausted model from the fallback list, or None if all exhausted."""
    for model_name in GEMINI_FALLBACK_MODELS:
        if model_name not in _exhausted_models:
            return model_name
    return None


def _generate_with_retry(model_name: str, contents, generation_config, stream=False):
    """
    Call generate_content with:
    1. RPM rate limit → wait and retry (same model)
    2. Daily RPD quota exhaustion → switch to next fallback model
    3. Other errors → raise immediately

    Returns: (response, model_name_actually_used)
    """
    current_model = model_name

    if current_model is None:
        raise RuntimeError(
            "All models exhausted their daily quota. "
            f"Tried: {', '.join(_exhausted_models)}. "
            "Please wait for quota reset or upgrade to a paid plan."
        )

    while True:
        model = genai.GenerativeModel(current_model)
        try:
            response = model.generate_content(
                contents,
                generation_config=generation_config,
                stream=stream,
            )
            return response, current_model

        except Exception as e:
            err_str = str(e)
            is_rate_limit = "429" in err_str or "quota" in err_str.lower() or "ResourceExhausted" in type(e).__name__

            if not is_rate_limit:
                raise

            if _is_daily_quota_error(err_str):
                # DAILY quota exhausted — mark this model and switch
                _exhausted_models.add(current_model)
                next_model = _get_available_model()

                if next_model is None:
                    # All models exhausted, nowhere to go
                    raise RuntimeError(
                        f"All models exhausted their daily quota. "
                        f"Tried: {', '.join(_exhausted_models)}. "
                        f"Please wait for quota reset or upgrade to a paid plan."
                    ) from e

                logger.warning(
                    f"Daily quota exhausted for {current_model}. "
                    f"Switching to fallback model: {next_model}"
                )
                current_model = next_model
                # Don't wait — different model has its own quota
                continue

            else:
                # RPM (per-minute) rate limit — wait and retry same model
                logger.warning(
                    f"RPM rate limited on {current_model}. "
                    f"Waiting {RPM_RETRY_WAIT}s..."
                )
                time.sleep(RPM_RETRY_WAIT)
                continue


# ── PDF upload ────────────────────────────────────────────────────────────────

def _upload_pdf(pdf_path: str, display_name: str) -> genai.types.File:
    """Upload a PDF to Gemini Files API with timeout protection."""
    logger.info(f"Uploading {display_name} to Gemini Files API...")
    uploaded = genai.upload_file(path=pdf_path, mime_type="application/pdf", display_name=display_name)

    start = time.time()
    while uploaded.state.name == "PROCESSING":
        if time.time() - start > FILE_PROCESSING_TIMEOUT:
            try:
                genai.delete_file(uploaded.name)
            except Exception:
                pass
            raise TimeoutError(
                f"Gemini file processing timed out after {FILE_PROCESSING_TIMEOUT}s. "
                "The PDF may be too large or corrupted."
            )
        time.sleep(2)
        uploaded = genai.get_file(uploaded.name)

    if uploaded.state.name != "ACTIVE":
        try:
            genai.delete_file(uploaded.name)
        except Exception:
            pass
        raise RuntimeError(f"Gemini file upload failed. State: {uploaded.state.name}")

    logger.info(f"Upload complete: {uploaded.name}")
    return uploaded


def _safe_delete_file(file_ref):
    try:
        genai.delete_file(file_ref.name)
    except Exception as e:
        logger.warning(f"Failed to delete Gemini file {file_ref.name}: {e}")


# ── JSON helpers ──────────────────────────────────────────────────────────────

def _sanitize_json(raw: str) -> str:
    """Clamp out-of-range integers that Gemini sometimes produces."""
    def clamp_int(m: re.Match) -> str:
        try:
            return str(min(max(int(m.group(0)), 0), 2_147_483_647))
        except ValueError:
            return "0"
    return re.sub(r'(?<!["\d\.])\b\d{11,}\b(?!["\d\.])', clamp_int, raw)


def _collect_stream(stream) -> tuple[str, bool]:
    """Collect a streamed Gemini response. Returns (text, was_truncated_by_tokens)."""
    parts = []
    finish_reason = None
    for chunk in stream:
        try:
            if chunk.text:
                parts.append(chunk.text)
        except Exception:
            # chunk.text raises if no valid Part exists — skip silently
            pass
        try:
            if chunk.candidates:
                fr = chunk.candidates[0].finish_reason
                if fr:
                    finish_reason = fr.name
        except Exception:
            pass
    text = "".join(parts)
    was_truncated = finish_reason == "MAX_TOKENS"
    logger.info(f"Stream collected: {len(text)} chars, finish_reason={finish_reason}")
    return text, was_truncated


def _parse_extraction(raw: str) -> TextbookExtraction:
    """Parse Gemini JSON → TextbookExtraction, with sanitize + truncation repair."""
    sanitized = _sanitize_json(raw)
    try:
        return TextbookExtraction.model_validate_json(sanitized)
    except Exception:
        pass
    logger.warning("Direct parse failed — attempting JSON truncation repair...")
    repaired = repair_truncated_json(sanitized)
    return TextbookExtraction.model_validate_json(repaired)


# ── Pass 1: TOC extraction ────────────────────────────────────────────────────

def extract_toc(
    pdf_path: str,
    subject_name: str,
    board: str,
    grade: str,
    medium: str,
) -> TOCExtraction:
    """Pass 1 — extract Table of Contents from the PDF."""
    uploaded = _upload_pdf(pdf_path, display_name=f"TOC_{subject_name}")
    try:
        model_name = _get_available_model()
        prompt = build_toc_prompt(subject_name, board, grade, medium)
        schema = _to_gemini_schema(TOCExtraction)
        gen_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.1,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )

        logger.info(f"Pass 1: Extracting TOC using model {model_name}...")
        response, used_model = _generate_with_retry(
            model_name, [uploaded, prompt], gen_config,
        )
        toc = TOCExtraction.model_validate_json(response.text)
        logger.info(f"TOC extracted: {toc.total_chapters} chapters found (model: {used_model})")
        return toc
    finally:
        _safe_delete_file(uploaded)


# ── Pass 2 (descriptive): per-chapter extraction ──────────────────────────────

def _parse_single_chapter(raw: str) -> SingleChapterExtraction:
    """Parse Gemini JSON → SingleChapterExtraction, with sanitize + truncation repair."""
    sanitized = _sanitize_json(raw)
    try:
        return SingleChapterExtraction.model_validate_json(sanitized)
    except Exception:
        pass
    logger.warning("Direct parse failed — attempting JSON truncation repair...")
    repaired = repair_truncated_json(sanitized)
    return SingleChapterExtraction.model_validate_json(repaired)


def _extract_single_chapter(
    uploaded,
    subject_name: str,
    board: str,
    grade: str,
    medium: str,
    ch_info: dict,
    idx: int,
    total: int,
    gen_config,
) -> Chapter:
    """Extract a single chapter with retry. Thread-safe worker function."""
    ch_num = ch_info["chapter_number"]
    ch_name = ch_info["name"]
    max_retries = 3

    prompt = build_single_chapter_prompt(
        subject_name, board, grade, medium, ch_num, ch_name
    )

    for attempt in range(1, max_retries + 1):
        model_name = _get_available_model()
        attempt_label = f" (attempt {attempt})" if attempt > 1 else ""
        logger.info(
            f"Chapter {idx}/{total}: "
            f"#{ch_num} \"{ch_name}\"{attempt_label} "
            f"using model {model_name}"
        )

        try:
            stream, used_model = _generate_with_retry(
                model_name, [uploaded, prompt], gen_config, stream=True
            )
            raw, was_truncated = _collect_stream(stream)

            if not raw.strip():
                raise ValueError("Gemini returned empty response (no content)")

            single = _parse_single_chapter(raw)

            # Force chapter_number and sort_order from TOC (don't trust Gemini)
            chapter = Chapter(
                chapter_number=ch_num,
                name=single.name or ch_name,
                description=single.description or f"Chapter {ch_num}: {ch_name}",
                content=single.content,
                sort_order=ch_num,
                topics=[],  # descriptive mode: always empty
            )
            logger.info(
                f"  Chapter {idx} OK: \"{chapter.name}\" "
                f"(content: {'yes' if chapter.content else 'no'}) "
                f"(model: {used_model})"
            )
            return chapter

        except Exception as e:
            logger.error(f"  Chapter {idx} attempt {attempt} FAILED: {e}")
            if attempt < max_retries:
                logger.info(f"  Retrying chapter #{ch_num} in 5s...")
                time.sleep(5)

    logger.error(
        f"  Chapter {idx} FAILED after {max_retries} attempts. "
        f"Creating stub for #{ch_num}."
    )
    return Chapter(
        chapter_number=ch_num,
        name=ch_name,
        description=f"[Extraction failed — please edit manually] Chapter {ch_num}: {ch_name}",
        content=None,
        sort_order=ch_num,
        topics=[],
    )


def _extract_descriptive(
    pdf_path: str,
    subject_name: str,
    board: str,
    grade: str,
    medium: str,
    toc_chapters: list[dict],
) -> TextbookExtraction:
    """
    Descriptive mode: extract ONE chapter at a time using SingleChapterExtraction.
    Processes chapters sequentially to avoid gRPC connection failures.

    Each chapter gets its own API call — no output token overflow, no dropped chapters.
    N chapters = N API calls + 1 TOC call.
    """
    uploaded = _upload_pdf(pdf_path, display_name=f"FULL_{subject_name}")
    try:
        schema = _to_gemini_schema(SingleChapterExtraction)

        gen_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.1,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )

        total = len(toc_chapters)
        all_chapters: list[Chapter] = []

        for idx, ch_info in enumerate(toc_chapters, 1):
            chapter = _extract_single_chapter(
                uploaded, subject_name, board, grade, medium,
                ch_info, idx, total, gen_config,
            )
            all_chapters.append(chapter)

        extraction = TextbookExtraction(
            metadata=ExtractionMetadata(
                total_chapters_found=len(all_chapters),
                confidence="high" if len(all_chapters) == len(toc_chapters) else "medium",
                notes=f"Extracted {len(all_chapters)} chapters sequentially.",
            ),
            chapters=all_chapters,
        )
        _log_extraction_stats(extraction)
        return extraction

    finally:
        _safe_delete_file(uploaded)


# ── Pass 2 (standard): whole-book extraction with continuation ────────────────

def _extract_standard(
    pdf_path: str,
    subject_name: str,
    board: str,
    grade: str,
    medium: str,
    toc_chapters: list[dict],
) -> TextbookExtraction:
    """Standard mode: single-shot with continuation fallback."""
    uploaded = _upload_pdf(pdf_path, display_name=f"FULL_{subject_name}")
    try:
        prompt = build_extraction_prompt(
            subject_name, board, grade, medium, toc_chapters, is_descriptive=False
        )
        schema = _to_gemini_schema(TextbookExtraction)
        gen_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.1,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        expected_chapters = len(toc_chapters)
        model_name = _get_available_model()

        logger.info(f"Pass 2: Extracting full hierarchy using {model_name}...")
        stream, used_model = _generate_with_retry(
            model_name, [uploaded, prompt], gen_config, stream=True
        )
        raw_text, _ = _collect_stream(stream)

        extraction = _try_parse_and_validate(raw_text, expected_chapters)
        if extraction:
            _log_extraction_stats(extraction)
            return extraction

        for attempt in range(1, MAX_CONTINUATION_ATTEMPTS + 1):
            model_name = _get_available_model()
            logger.info(f"Continuation {attempt}/{MAX_CONTINUATION_ATTEMPTS} using {model_name}...")
            continuation_prompt = (
                f"{prompt}\n\n"
                f"== RETRY REQUIRED ==\n\n"
                f"Your previous response was incomplete — it missed chapters. "
                f"You MUST include ALL {expected_chapters} chapters. "
                f"Be concise: 1-sentence descriptions, 3-6 word subtopic names. "
                f"Do NOT drop any chapters. Produce complete, valid JSON."
            )
            stream, _ = _generate_with_retry(
                model_name, [uploaded, continuation_prompt], gen_config, stream=True
            )
            raw_text, _ = _collect_stream(stream)
            extraction = _try_parse_and_validate(raw_text, expected_chapters)
            if extraction:
                logger.info(f"Continuation {attempt} succeeded.")
                _log_extraction_stats(extraction)
                return extraction

        logger.error("All continuation attempts failed. Returning best-effort partial.")
        try:
            repaired = repair_truncated_json(_sanitize_json(raw_text))
            extraction = TextbookExtraction.model_validate_json(repaired)
            _log_extraction_stats(extraction, partial=True)
            return extraction
        except Exception as last_err:
            raise RuntimeError(
                f"Extraction failed after {MAX_CONTINUATION_ATTEMPTS} attempts. "
                f"Last error: {last_err}."
            ) from last_err

    finally:
        _safe_delete_file(uploaded)


def _try_parse_and_validate(
    raw_text: str,
    expected_chapters: int,
    min_ratio: float = 0.9,
) -> TextbookExtraction | None:
    """Parse + validate chapter count. Returns None if parse fails or count is low."""
    try:
        extraction = _parse_extraction(raw_text)
    except Exception as e:
        logger.warning(f"Parse failed: {e}")
        return None

    got = len(extraction.chapters)
    needed = int(expected_chapters * min_ratio)
    if got < needed:
        logger.warning(f"Chapter count: {got}/{expected_chapters} (need >= {needed})")
        return None
    return extraction


# ── Public entry point ────────────────────────────────────────────────────────

def extract_full(
    pdf_path: str,
    subject_name: str,
    board: str,
    grade: str,
    medium: str,
    toc_chapters: list[dict],
    is_descriptive: bool = False,
) -> TextbookExtraction:
    """
    Pass 2 — extract full Chapter → Topic → Subtopic hierarchy.

    Descriptive (language/literature): one chapter per API call (zero data loss).
    Standard (science/math): single call with continuation fallback.
    Both modes use model rotation if daily quota is exhausted.
    """
    if is_descriptive:
        logger.info(
            f"Pass 2 (descriptive): {len(toc_chapters)} chapters, "
            f"extracting one-by-one..."
        )
        return _extract_descriptive(
            pdf_path, subject_name, board, grade, medium, toc_chapters
        )
    else:
        logger.info("Pass 2 (standard): extracting full hierarchy...")
        return _extract_standard(
            pdf_path, subject_name, board, grade, medium, toc_chapters
        )


def _log_extraction_stats(extraction: TextbookExtraction, partial: bool = False):
    label = "PARTIAL extraction" if partial else "Extraction"
    logger.info(
        f"{label} complete: {len(extraction.chapters)} chapters, "
        f"{sum(len(c.topics) for c in extraction.chapters)} topics, "
        f"{sum(len(t.subtopics) for c in extraction.chapters for t in c.topics)} subtopics"
    )


# ── Pass 3: Question extraction ───────────────────────────────────────────────

def _parse_chapter_questions(raw: str) -> ChapterQuestions:
    """Parse Gemini JSON → ChapterQuestions, with sanitize + truncation repair."""
    sanitized = _sanitize_json(raw)
    try:
        return ChapterQuestions.model_validate_json(sanitized)
    except Exception:
        pass
    logger.warning("Direct parse failed — attempting JSON truncation repair...")
    repaired = repair_truncated_json(sanitized)
    return ChapterQuestions.model_validate_json(repaired)


def _extract_single_chapter_questions(
    uploaded,
    subject_name: str,
    board: str,
    grade: str,
    medium: str,
    ch_info: dict,
    idx: int,
    total: int,
    gen_config,
) -> ChapterQuestions | None:
    """Extract questions from a single chapter with retry."""
    ch_num = ch_info["chapter_number"]
    ch_name = ch_info["name"]
    max_retries = 3

    prompt = build_question_extraction_prompt(
        subject_name, board, grade, medium, ch_num, ch_name
    )

    for attempt in range(1, max_retries + 1):
        model_name = _get_available_model()
        attempt_label = f" (attempt {attempt})" if attempt > 1 else ""
        logger.info(
            f"Questions {idx}/{total}: "
            f"#{ch_num} \"{ch_name}\"{attempt_label} "
            f"using model {model_name}"
        )

        try:
            stream, used_model = _generate_with_retry(
                model_name, [uploaded, prompt], gen_config, stream=True
            )
            raw, was_truncated = _collect_stream(stream)

            if not raw.strip():
                raise ValueError("Gemini returned empty response (no content)")

            chapter_qs = _parse_chapter_questions(raw)

            # Force chapter metadata from TOC
            chapter_qs.chapter_number = ch_num
            chapter_qs.chapter_name = ch_name

            total_qs = sum(len(qs.questions) for qs in chapter_qs.question_sets)
            logger.info(
                f"  Questions OK: #{ch_num} \"{ch_name}\" → "
                f"{len(chapter_qs.question_sets)} sets, {total_qs} questions "
                f"(model: {used_model})"
            )
            return chapter_qs

        except Exception as e:
            logger.error(f"  Questions {idx} attempt {attempt} FAILED: {e}")
            if attempt < max_retries:
                logger.info(f"  Retrying questions #{ch_num} in 5s...")
                time.sleep(5)

    logger.error(
        f"  Questions for chapter {idx} FAILED after {max_retries} attempts. "
        f"Skipping #{ch_num}."
    )
    return ChapterQuestions(
        chapter_number=ch_num,
        chapter_name=ch_name,
        question_sets=[],
    )


def extract_questions(
    pdf_path: str,
    subject_name: str,
    board: str,
    grade: str,
    medium: str,
    toc_chapters: list[dict],
) -> list[ChapterQuestions]:
    """
    Pass 3 — extract questions from each chapter.

    Processes chapters sequentially (one API call per chapter).
    Returns a list of ChapterQuestions objects.
    """
    uploaded = _upload_pdf(pdf_path, display_name=f"QUESTIONS_{subject_name}")
    try:
        schema = _to_gemini_schema(ChapterQuestions)
        gen_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.1,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )

        total = len(toc_chapters)
        all_questions: list[ChapterQuestions] = []

        for idx, ch_info in enumerate(toc_chapters, 1):
            chapter_qs = _extract_single_chapter_questions(
                uploaded, subject_name, board, grade, medium,
                ch_info, idx, total, gen_config,
            )
            if chapter_qs:
                all_questions.append(chapter_qs)

        total_sets = sum(len(cq.question_sets) for cq in all_questions)
        total_qs = sum(
            len(q) for cq in all_questions
            for qs in cq.question_sets
            for q in [qs.questions]
        )
        logger.info(
            f"Pass 3 complete: {len(all_questions)} chapters, "
            f"{total_sets} question sets, {total_qs} questions"
        )
        return all_questions

    finally:
        _safe_delete_file(uploaded)


# ── SVG regeneration (single question) ───────────────────────────────────────

def regenerate_svg(image_description: str) -> str:
    """
    Generate an SVG diagram from an image description.
    Single Gemini API call — no PDF upload needed.
    Returns the SVG string.
    """
    prompt = f"""You are a precise mathematical diagram renderer. Generate an SVG diagram for this description.

DESCRIPTION:
{image_description}

CRITICAL SVG GENERATION RULES:

1. COORDINATE SYSTEM & SCALING:
   - Use viewBox="0 0 400 300"
   - Place the origin (0,0) at pixel (200, 150) — center of the viewBox
   - Determine the axis range from the description (e.g. -5 to 8 on X, -4 to 6 on Y)
   - Calculate pixels_per_unit = available_space / axis_range (e.g. 160px / 13 units ≈ 12.3 px/unit)
   - For each mathematical point (x,y): pixel_x = 200 + x * pixels_per_unit, pixel_y = 150 - y * pixels_per_unit

2. AXES (draw first):
   - X-axis: horizontal line at pixel y=150, spanning the full width with arrow tips
   - Y-axis: vertical line at pixel x=200, spanning the full height with arrow tips
   - Label axes with "X", "X'", "Y", "Y'" at the ends
   - Add tick marks every 1 unit with small labels (font-size 9-10)
   - Mark the origin "O" at (200, 150)

3. GRID (optional, light):
   - Light gray (#e8e8e8) dashed lines at each integer unit
   - stroke-width="0.5" stroke-dasharray="2,2"

4. PLOTTING POINTS:
   - Use <circle cx="__" cy="__" r="4" fill="color"/> at EXACT computed pixel positions
   - Label each point with its coordinates using <text> offset slightly from the dot
   - Use font-size="10" for point labels

5. LINES & CURVES:
   - For linear equations y=mx+b: compute two extreme points on the axis range, draw <line> between them
   - For line segments: compute exact start/end pixel positions
   - Use stroke-width="2" for main lines, "1.5" for secondary lines
   - Use distinct colors: #e74c3c (red), #2563eb (blue), #16a34a (green), #ea580c (orange)
   - Label each line with its equation using <text> near the line

6. GEOMETRIC SHAPES:
   - Triangles/polygons: compute all vertices at exact pixel positions, use <polygon>
   - Circles: use <circle> with computed center and radius in pixel units
   - Angles: use small <path> arcs near the vertex, label with degree value

7. STYLE:
   - White background rectangle: <rect width="400" height="300" fill="#ffffff"/>
   - All text: font-family="sans-serif", fill="#1a1a2e"
   - No external fonts, no CSS classes, inline styles only
   - No <style> blocks, no <defs> unless needed for arrowheads

8. OUTPUT:
   - Output ONLY the raw SVG string, starting with <svg and ending with </svg>
   - No markdown, no code fences, no explanation
   - The SVG must be valid XML"""

    gen_config = genai.GenerationConfig(
        temperature=0.1,  # very low for mathematical precision
        max_output_tokens=8192,  # diagrams can be complex
    )

    model_name = GEMINI_MODEL if GEMINI_MODEL not in _exhausted_models else _get_available_model()
    if not model_name:
        model_name = GEMINI_FALLBACK_MODELS[0]

    try:
        response, _ = _generate_with_retry(model_name, prompt, gen_config)

        # Handle safety filter blocks (finish_reason 2)
        if not response.candidates or not response.candidates[0].content.parts:
            raise ValueError("Gemini returned no content — the diagram description may have triggered a safety filter. Try simplifying the description.")

        svg_text = response.text.strip()
    except ValueError as e:
        if "finish_reason" in str(e) or "quick accessor" in str(e):
            raise ValueError(
                "Gemini blocked this SVG generation (safety filter). "
                "Try rephrasing the image description to be more explicit about the mathematical content."
            )
        raise

    # Clean up: remove markdown fences if Gemini wraps it
    if svg_text.startswith("```"):
        svg_text = re.sub(r'^```(?:svg|xml)?\s*\n?', '', svg_text)
        svg_text = re.sub(r'\n?```\s*$', '', svg_text)

    # Ensure it starts with <svg
    svg_start = svg_text.find('<svg')
    if svg_start > 0:
        svg_text = svg_text[svg_start:]
    elif svg_start == -1:
        raise ValueError("Gemini did not return valid SVG. Try regenerating.")

    # Ensure it ends with </svg>
    svg_end = svg_text.rfind('</svg>')
    if svg_end > 0:
        svg_text = svg_text[:svg_end + 6]

    return svg_text
