import os
import uuid
import logging
import asyncio
import tempfile
from typing import Optional

from pydantic import BaseModel, ValidationError

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import aiofiles

from models import (
    JobStatus, JobResult, InsertRequest, InsertResult,
    UploadMetadata, TOCExtraction, TextbookExtraction, ChapterQuestions,
)
from gemini_service import extract_toc, extract_full, extract_questions, regenerate_svg
from validator import validate_extraction
from inserter import insert_extraction

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="SyllabusService", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory job store (sufficient for local admin tool) ────────────────────
jobs: dict[str, dict] = {}       # job_id → {"status", "progress", "result", "error", ...}
temp_files: dict[str, str] = {}  # job_id → temp pdf path


# ── Background processing task ───────────────────────────────────────────────

async def _process_job(job_id: str, pdf_path: str, meta: UploadMetadata):
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = "Pass 1: Extracting Table of Contents..."

        # Run blocking Gemini calls in thread pool (they're synchronous)
        loop = asyncio.get_event_loop()

        toc: TOCExtraction = await loop.run_in_executor(
            None,
            extract_toc,
            pdf_path,
            meta.subject_name,
            meta.board,
            meta.grade,
            meta.medium,
        )

        n_batches = -(-toc.total_chapters // 6)  # ceil div, matches DESCRIPTIVE_BATCH_SIZE
        jobs[job_id]["progress"] = (
            f"Pass 1 done — {toc.total_chapters} chapters found. "
            + (
                f"Pass 2: Extracting in {n_batches} batches (descriptive mode)..."
                if meta.is_descriptive
                else "Pass 2: Extracting full hierarchy..."
            )
        )
        jobs[job_id]["toc"] = toc

        toc_dicts = [{"chapter_number": c.chapter_number, "name": c.name} for c in toc.chapters]

        extraction: TextbookExtraction = await loop.run_in_executor(
            None,
            extract_full,
            pdf_path,
            meta.subject_name,
            meta.board,
            meta.grade,
            meta.medium,
            toc_dicts,
            meta.is_descriptive,
        )

        jobs[job_id]["progress"] = "Validating extraction..."
        validation = validate_extraction(toc, extraction, is_descriptive=meta.is_descriptive)

        # ── Pass 3: Question extraction (optional) ──────────────
        chapter_questions = None
        if meta.extract_questions:
            jobs[job_id]["progress"] = "Pass 3: Extracting questions per chapter..."
            chapter_questions = await loop.run_in_executor(
                None,
                extract_questions,
                pdf_path,
                meta.subject_name,
                meta.board,
                meta.grade,
                meta.medium,
                toc_dicts,
            )

        jobs[job_id]["status"] = "done"
        jobs[job_id]["progress"] = "Extraction complete. Ready for review."
        jobs[job_id]["extraction"] = extraction
        jobs[job_id]["validation_warning"] = validation.get("warning")
        jobs[job_id]["questions"] = chapter_questions

    except ValueError as e:
        # Hard data-loss error (validation, missing chapters, etc.)
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
        logger.error(f"Job {job_id} failed validation: {e}")
    except ValidationError as e:
        # Gemini returned JSON that doesn't match our Pydantic models
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = (
            f"Gemini response didn't match expected schema. "
            f"This can happen with unusually structured PDFs. "
            f"Errors: {e.error_count()} validation errors."
        )
        logger.error(f"Job {job_id} schema mismatch: {e}")
    except TimeoutError as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
        logger.error(f"Job {job_id} timed out: {e}")
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = f"Unexpected error: {str(e)}"
        logger.exception(f"Job {job_id} crashed")
    finally:
        # PDF kept alive for review page — deleted on /approve or server restart
        pass


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/upload", response_model=JobStatus)
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    region: str = Form("Asia"),
    country: str = Form("India"),
    board: str = Form("Maharashtra State Board"),
    grade: str = Form("Class 10"),
    stream: str = Form("General"),
    medium: str = Form("English"),
    medium_code: str = Form("en"),
    subject_name: str = Form(...),
    # Optional UUIDs from cascade DB mode (empty string = not provided)
    education_system_id: str = Form(""),
    education_level_id: str = Form(""),
    grade_id: str = Form(""),
    stream_id: str = Form(""),
    is_descriptive: str = Form("false"),  # "true" or "false" from checkbox
    extract_questions: str = Form("false"),  # "true" or "false" from checkbox
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # Save PDF to temp file
    job_id = str(uuid.uuid4())
    suffix = f"_{file.filename}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        pdf_path = tmp.name

    async with aiofiles.open(pdf_path, "wb") as out:
        content = await file.read()
        await out.write(content)

    meta = UploadMetadata(
        region=region, country=country, board=board,
        grade=grade, stream=stream, medium=medium,
        medium_code=medium_code, subject_name=subject_name,
        is_descriptive=is_descriptive.lower() in ("true", "1", "on"),
        extract_questions=extract_questions.lower() in ("true", "1", "on"),
        education_system_id=education_system_id or None,
        education_level_id=education_level_id or None,
        grade_id=grade_id or None,
        stream_id=stream_id or None,
    )

    jobs[job_id] = {
        "status": "pending",
        "progress": "Queued. Starting upload to Gemini...",
        "meta": meta,
        "toc": None,
        "extraction": None,
        "validation_warning": None,
        "questions": None,
        "error": None,
    }
    temp_files[job_id] = pdf_path

    background_tasks.add_task(_process_job, job_id, pdf_path, meta)

    return JobStatus(job_id=job_id, status="pending", progress="Processing started.")


@app.get("/status/{job_id}", response_model=JobStatus)
def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        warning=job.get("validation_warning"),
        error=job.get("error"),
    )


@app.get("/result/{job_id}", response_model=JobResult)
def get_result(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job["status"] != "done":
        raise HTTPException(status_code=400, detail=f"Job not ready. Status: {job['status']}")

    toc = job["toc"]
    return JobResult(
        job_id=job_id,
        metadata=job["meta"],
        extraction=job["extraction"],
        toc_chapters=toc.chapters,
        validation_warning=job.get("validation_warning"),
        questions=job.get("questions"),
    )


@app.post("/approve", response_model=InsertResult)
def approve_and_insert(req: InsertRequest):
    """Insert the (possibly edited) extraction into Supabase."""
    job = jobs.get(req.job_id)
    if not job and req.job_id != "manual":
        raise HTTPException(status_code=404, detail="Job not found.")

    try:
        result = insert_extraction(req.extraction, req.metadata, questions=req.questions)
        # Clean up PDF after successful insert
        pdf_path = temp_files.pop(req.job_id, None)
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
        # Mark job as inserted
        if job:
            job["status"] = "inserted"
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RegenerateSvgRequest(BaseModel):
    job_id: str
    image_description: str


@app.post("/regenerate-svg")
async def regenerate_svg_endpoint(req: RegenerateSvgRequest):
    """Regenerate an SVG diagram from an image description using Gemini."""
    if not req.image_description:
        raise HTTPException(status_code=400, detail="image_description is required")
    try:
        svg = regenerate_svg(req.image_description)
        return {"image_svg": svg}
    except ValueError as e:
        # Safety filter, bad output — user can retry
        logger.warning(f"SVG regeneration issue: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"SVG regeneration failed: {e}")
        raise HTTPException(status_code=500, detail=f"SVG generation failed: {str(e)}")


@app.get("/health")
def health():
    return {"status": "ok", "service": "SyllabusService"}


@app.get("/pdf/{job_id}")
def serve_pdf(job_id: str):
    """Serve the uploaded PDF for the review page's PDF.js viewer."""
    pdf_path = temp_files.get(job_id)
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found (may have expired).")
    return FileResponse(pdf_path, media_type="application/pdf")


# ── Cascade lookup endpoints (for frontend dropdowns) ────────────────────────

from inserter import supabase as db

@app.get("/api/regions")
def list_regions():
    res = db.table("regions").select("id, name, code").order("sort_order").execute()
    return res.data

@app.get("/api/countries")
def list_countries(region_id: str = None):
    q = db.table("countries").select("id, name, iso_code, flag_emoji").eq("is_active", True)
    if region_id:
        q = q.eq("region_id", region_id)
    return q.order("sort_order").execute().data

@app.get("/api/systems")
def list_systems(country_id: str = None):
    q = db.table("education_systems").select("id, name, short_name, system_type").eq("is_active", True)
    if country_id:
        q = q.eq("country_id", country_id)
    return q.order("sort_order").execute().data

@app.get("/api/levels")
def list_levels(system_id: str):
    res = db.table("education_levels").select("id, name, level_type").eq("education_system_id", system_id).order("sort_order").execute()
    return res.data

@app.get("/api/grades")
def list_grades(level_id: str):
    res = db.table("grades").select("id, name, display_name, numeric_value").eq("education_level_id", level_id).order("sort_order").execute()
    return res.data

@app.get("/api/streams")
def list_streams(grade_id: str):
    res = db.table("streams").select("id, name, is_default").eq("grade_id", grade_id).order("sort_order").execute()
    return res.data


# ── Library endpoints (view & delete inserted subjects) ───────────────────────

@app.get("/api/library")
def list_library_subjects():
    """List all inserted subjects with counts and hierarchy info.
    Uses nested JOINs (2-3 Supabase queries total, not N×5).
    """
    # Query 1: Single nested JOIN — subjects → chapters → topics → subtopics
    tree_result = db.table("subjects").select(
        "id, name, icon_name, medium, medium_code, chapter_count, is_active, created_at, stream_id, "
        "chapters(id, topics(id, subtopics(id)))"
    ).order("created_at", desc=True).execute().data or []

    # Query 2: Get all question sets + question counts in one call
    all_chapter_ids = []
    for s in tree_result:
        for c in (s.get("chapters") or []):
            all_chapter_ids.append(c["id"])

    qs_counts = {}  # chapter_id → {sets: N, questions: N}
    if all_chapter_ids:
        qs_result = db.table("question_sets").select(
            "id, chapter_id, questions(id)"
        ).in_("chapter_id", all_chapter_ids).execute().data or []

        for qs in qs_result:
            cid = qs["chapter_id"]
            if cid not in qs_counts:
                qs_counts[cid] = {"sets": 0, "questions": 0}
            qs_counts[cid]["sets"] += 1
            qs_counts[cid]["questions"] += len(qs.get("questions") or [])

    # Query 3: Resolve stream → grade → level → system hierarchy in one pass
    stream_ids = list({s["stream_id"] for s in tree_result if s.get("stream_id")})
    stream_cache = {}
    if stream_ids:
        streams = db.table("streams").select(
            "id, name, grade_id, "
            "grades:grade_id(id, name, education_level_id, "
            "education_levels:education_level_id(id, name, education_system_id, "
            "education_systems:education_system_id(id, name, short_name)))"
        ).in_("id", stream_ids).execute().data or []

        for st in streams:
            grade = st.get("grades") or {}
            level = grade.get("education_levels") or {}
            system = level.get("education_systems") or {}
            stream_cache[st["id"]] = {
                "stream_name": st.get("name", "Unknown"),
                "grade_name": grade.get("name", "Unknown"),
                "board_name": system.get("short_name") or system.get("name") or "Unknown",
            }

    # Build response from nested tree
    results = []
    for subj in tree_result:
        chapters = subj.get("chapters") or []
        topic_count = 0
        subtopic_count = 0
        total_qs_sets = 0
        total_questions = 0

        for ch in chapters:
            topics = ch.get("topics") or []
            topic_count += len(topics)
            for t in topics:
                subtopic_count += len(t.get("subtopics") or [])
            ch_qs = qs_counts.get(ch["id"], {})
            total_qs_sets += ch_qs.get("sets", 0)
            total_questions += ch_qs.get("questions", 0)

        hierarchy = stream_cache.get(subj.get("stream_id"), {})

        # Remove nested children from the response (just need counts)
        subj_flat = {k: v for k, v in subj.items() if k != "chapters"}
        results.append({
            **subj_flat,
            "board_name": hierarchy.get("board_name", "Unknown"),
            "grade_name": hierarchy.get("grade_name", "Unknown"),
            "stream_name": hierarchy.get("stream_name", "Unknown"),
            "topic_count": topic_count,
            "subtopic_count": subtopic_count,
            "question_set_count": total_qs_sets,
            "question_count": total_questions,
        })

    return results


@app.get("/api/library/{subject_id}")
def get_library_subject(subject_id: str):
    """Get full subject detail with chapter/topic/subtopic tree.
    Uses a single nested JOIN (1-2 Supabase queries total).
    """
    # Query 1: Single nested JOIN for full tree
    result = db.table("subjects").select(
        "*, chapters(*, topics(*, subtopics(*)))"
    ).eq("id", subject_id).limit(1).execute().data

    if not result:
        raise HTTPException(status_code=404, detail="Subject not found")

    subj = result[0]
    chapters = subj.pop("chapters", []) or []
    chapters.sort(key=lambda c: c.get("sort_order", 0))

    # Query 2: Question sets with nested questions
    all_chapter_ids = [c["id"] for c in chapters]
    qs_by_chapter = {}
    if all_chapter_ids:
        qs_result = db.table("question_sets").select(
            "*, questions(*)"
        ).in_("chapter_id", all_chapter_ids).order("sort_order").execute().data or []

        for qs in qs_result:
            cid = qs["chapter_id"]
            questions = qs.get("questions") or []
            questions.sort(key=lambda q: q.get("sort_order", 0))
            qs["question_count"] = len(questions)
            qs_by_chapter.setdefault(cid, []).append(qs)

    # Sort nested children and build tree
    for ch in chapters:
        topics = ch.get("topics") or []
        topics.sort(key=lambda t: t.get("sort_order", 0))
        for t in topics:
            subtopics = t.get("subtopics") or []
            subtopics.sort(key=lambda st: st.get("sort_order", 0))
            t["subtopics"] = subtopics
        ch["topics"] = topics
        ch["question_sets"] = qs_by_chapter.get(ch["id"], [])

    return {"subject": subj, "chapters": chapters}


@app.delete("/api/library/{subject_id}")
def delete_library_subject(subject_id: str):
    """Cascade-delete a subject and all its children."""
    subj = db.table("subjects").select("id, name").eq("id", subject_id).limit(1).execute().data
    if not subj:
        raise HTTPException(status_code=404, detail="Subject not found")

    # Get all chapter IDs
    chapters = db.table("chapters").select("id").eq("subject_id", subject_id).execute().data or []
    chapter_ids = [c["id"] for c in chapters]

    deleted = {"questions": 0, "question_sets": 0, "subtopics": 0, "topics": 0, "chapters": 0}

    if chapter_ids:
        # Delete questions → question_sets
        q_sets = db.table("question_sets").select("id").in_("chapter_id", chapter_ids).execute().data or []
        q_set_ids = [qs["id"] for qs in q_sets]
        if q_set_ids:
            qs_del = db.table("questions").delete().in_("question_set_id", q_set_ids).execute()
            deleted["questions"] = len(qs_del.data or [])
            sets_del = db.table("question_sets").delete().in_("chapter_id", chapter_ids).execute()
            deleted["question_sets"] = len(sets_del.data or [])

        # Delete subtopics → topics
        topics = db.table("topics").select("id").in_("chapter_id", chapter_ids).execute().data or []
        topic_ids = [t["id"] for t in topics]
        if topic_ids:
            st_del = db.table("subtopics").delete().in_("topic_id", topic_ids).execute()
            deleted["subtopics"] = len(st_del.data or [])
        t_del = db.table("topics").delete().in_("chapter_id", chapter_ids).execute()
        deleted["topics"] = len(t_del.data or [])

        # Delete chapters
        ch_del = db.table("chapters").delete().eq("subject_id", subject_id).execute()
        deleted["chapters"] = len(ch_del.data or [])

    # Delete subject
    db.table("subjects").delete().eq("id", subject_id).execute()

    logger.info(f"Deleted subject '{subj[0]['name']}' ({subject_id}): {deleted}")
    return {"success": True, "subject_name": subj[0]["name"], "deleted": deleted}


class UpdateIconRequest(BaseModel):
    icon_name: str
    icon_svg: Optional[str] = None


@app.patch("/api/library/{subject_id}/icon")
def update_subject_icon(subject_id: str, req: UpdateIconRequest):
    """Update the icon_name (and optionally icon_svg) for a subject."""
    subj = db.table("subjects").select("id, name").eq("id", subject_id).limit(1).execute().data
    if not subj:
        raise HTTPException(status_code=404, detail="Subject not found")

    update_data = {"icon_name": req.icon_name}
    if req.icon_svg is not None:
        update_data["icon_svg"] = req.icon_svg

    db.table("subjects").update(update_data).eq("id", subject_id).execute()
    logger.info(f"Updated icon for '{subj[0]['name']}' to '{req.icon_name}' (svg={'yes' if req.icon_svg else 'no'})")
    return {"success": True, "subject_name": subj[0]["name"], "icon_name": req.icon_name}


# ── Serve frontend ────────────────────────────────────────────────────────────
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/review")
    def serve_review():
        return FileResponse(os.path.join(frontend_dir, "review.html"))

    @app.get("/library")
    def serve_library():
        return FileResponse(os.path.join(frontend_dir, "library.html"))
