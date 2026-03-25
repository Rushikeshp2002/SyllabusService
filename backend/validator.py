import re
import logging
from models import TextbookExtraction, TOCExtraction

logger = logging.getLogger(__name__)


def _normalize_name(name: str) -> str:
    """Normalize a chapter name for fuzzy comparison.
    Strips whitespace, punctuation, and lowercases everything."""
    name = name.lower().strip()
    # Remove all punctuation and extra whitespace
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def validate_extraction(
    toc: TOCExtraction,
    extraction: TextbookExtraction,
    is_descriptive: bool = False,
) -> dict:
    """
    Cross-checks the full extraction against the TOC.
    Returns {"ok": True} or {"warning": "..."}.
    Uses fuzzy name matching to avoid false alarms from minor spelling differences.
    """
    toc_normalized = {_normalize_name(ch.name) for ch in toc.chapters}
    extracted_normalized = {_normalize_name(ch.name) for ch in extraction.chapters}

    missing = toc_normalized - extracted_normalized
    extra = extracted_normalized - toc_normalized

    warnings = []

    # Check by chapter count — more reliable than name matching
    if len(extraction.chapters) < len(toc.chapters):
        warnings.append(
            f"Extracted {len(extraction.chapters)}/{len(toc.chapters)} chapters "
            f"(missing {len(toc.chapters) - len(extraction.chapters)})"
        )

    if missing:
        # Get original names for display
        missing_original = [
            ch.name for ch in toc.chapters
            if _normalize_name(ch.name) in missing
        ]
        warnings.append(
            f"{len(missing)} chapter name(s) from TOC not found in extraction: "
            + ", ".join(missing_original)
        )

    if extraction.metadata.confidence == "low":
        warnings.append(
            "Gemini flagged LOW confidence — textbook has unclear structure. "
            "Review every chapter carefully."
        )
    elif extraction.metadata.confidence == "medium":
        warnings.append("Gemini flagged MEDIUM confidence — some ambiguity in structure.")

    if extraction.metadata.notes:
        warnings.append(f"Gemini notes: {extraction.metadata.notes}")

    # Check for chapters with 0 topics (skip for descriptive subjects where topics are optional)
    if not is_descriptive:
        empty_chapters = [c.name for c in extraction.chapters if len(c.topics) == 0]
        if empty_chapters:
            warnings.append(
                f"{len(empty_chapters)} chapter(s) have 0 topics extracted: "
                + ", ".join(empty_chapters)
            )

    if warnings:
        return {"warning": " | ".join(warnings)}

    return {"ok": True}
