import logging
from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_KEY
from models import TextbookExtraction, UploadMetadata, InsertResult, ChapterQuestions

logger = logging.getLogger(__name__)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def _require(table: str, filters: dict, label: str) -> str:
    """Look up a single row. Raise ValueError if not found. No auto-creation."""
    query = supabase.table(table).select("id")
    for k, v in filters.items():
        query = query.eq(k, v)
    result = query.limit(1).execute()
    if not result.data:
        raise ValueError(
            f"MISSING: {label} not found in '{table}' with filters {filters}. "
            f"Run seed.sql first to populate the hierarchy."
        )
    return result.data[0]["id"]


def _resolve_stream_id(meta: UploadMetadata) -> str:
    """
    Resolve the stream_id for inserting a subject.
    Uses frontend-provided UUIDs if available, otherwise walks the
    hierarchy using human-readable names. Never creates rows — all
    parent data must exist from seed.sql.
    """

    # ── Fast path: frontend already resolved the full cascade ────────────
    if meta.stream_id:
        # Verify it actually exists
        check = supabase.table("streams").select("id").eq("id", meta.stream_id).limit(1).execute()
        if not check.data:
            raise ValueError(f"stream_id '{meta.stream_id}' does not exist in database.")
        logger.info(f"Using frontend-resolved stream_id: {meta.stream_id}")
        return meta.stream_id

    # ── Slow path: resolve by name chain ─────────────────────────────────
    # Board lookup: try short_name match from known mappings
    BOARD_SHORT_NAMES = {
        "Maharashtra State Board": "MSBSHSE",
        "CBSE": "CBSE",
        "Central Board of Secondary Education": "CBSE",
        "ICSE": "ICSE",
        "Council for the Indian School Certificate Examinations": "ICSE",
        "NIOS": "NIOS",
    }
    short_name = BOARD_SHORT_NAMES.get(meta.board)

    if meta.education_system_id:
        system_id = meta.education_system_id
    elif short_name:
        system_id = _require("education_systems", {"short_name": short_name}, f"Board '{meta.board}'")
    else:
        system_id = _require("education_systems", {"name": meta.board}, f"Board '{meta.board}'")

    # Level: infer from grade name
    GRADE_TO_LEVEL_TYPE = {
        "Class 1": "primary", "Class 2": "primary", "Class 3": "primary",
        "Class 4": "primary", "Class 5": "primary",
        "Class 6": "middle", "Class 7": "middle", "Class 8": "middle",
        "Class 9": "secondary", "Class 10": "secondary",
        "Class 11": "senior_secondary", "Class 12": "senior_secondary",
    }
    level_type = GRADE_TO_LEVEL_TYPE.get(meta.grade)

    if meta.education_level_id:
        level_id = meta.education_level_id
    elif level_type:
        level_id = _require(
            "education_levels",
            {"education_system_id": system_id, "level_type": level_type},
            f"Level for '{meta.grade}' in board"
        )
    else:
        raise ValueError(
            f"Cannot infer education level for grade '{meta.grade}'. "
            f"Use DB cascade mode or provide education_level_id."
        )

    # Grade
    if meta.grade_id:
        grade_id = meta.grade_id
    else:
        grade_id = _require(
            "grades",
            {"education_level_id": level_id, "name": meta.grade},
            f"Grade '{meta.grade}'"
        )

    # Stream
    stream_id = None
    # Try exact name match first
    res = supabase.table("streams").select("id").eq("grade_id", grade_id).eq("name", meta.stream).limit(1).execute()
    if res.data:
        stream_id = res.data[0]["id"]
    else:
        # Fall back to default stream
        res = supabase.table("streams").select("id").eq("grade_id", grade_id).eq("is_default", True).limit(1).execute()
        if res.data:
            stream_id = res.data[0]["id"]

    if not stream_id:
        raise ValueError(
            f"MISSING: No stream '{meta.stream}' or default stream found for grade '{meta.grade}'. "
            f"Run seed.sql first."
        )

    return stream_id


def _check_duplicate_subject(stream_id: str, name: str, medium_code: str):
    """Raise if subject already exists in this stream+medium combo."""
    res = (
        supabase.table("subjects")
        .select("id, name")
        .eq("stream_id", stream_id)
        .eq("name", name)
        .limit(1)
        .execute()
    )
    if res.data:
        raise ValueError(
            f"DUPLICATE: Subject '{name}' already exists in this stream "
            f"(existing id: {res.data[0]['id']}). Delete it first to re-insert."
        )


def insert_extraction(
    extraction: TextbookExtraction,
    meta: UploadMetadata,
    questions: list[ChapterQuestions] | None = None,
) -> InsertResult:
    """
    Insert the extracted textbook data into Supabase.

    Pre-conditions (enforced, not auto-created):
    1. Region, country, board, level, grade, stream MUST exist (from seed.sql)
    2. Subject must NOT already exist in the same stream+medium

    The inserter only CREATES: subject + chapters + topics + subtopics.
    If questions are provided, also inserts question_sets + questions.
    """
    logger.info(f"Starting insertion for: {meta.subject_name} ({meta.medium})")

    # ── Step 1: Resolve stream_id from the seeded hierarchy ────────────
    stream_id = _resolve_stream_id(meta)
    logger.info(f"Resolved stream_id: {stream_id}")

    # ── Step 2: Check for duplicate subject ──────────────────────
    _check_duplicate_subject(stream_id, meta.subject_name, meta.medium_code)

    # ── Step 3: Insert subject ───────────────────────────────
    subject_data = {
        "stream_id": stream_id,
        "name": meta.subject_name,
        "chapter_count": len(extraction.chapters),
        "sort_order": 1,
        "is_active": True,
    }
    # Only add medium columns if they exist in the table
    if meta.medium:
        subject_data["medium"] = meta.medium
    if meta.medium_code:
        subject_data["medium_code"] = meta.medium_code

    subject_res = supabase.table("subjects").insert(subject_data).execute()
    subject_id = subject_res.data[0]["id"]
    logger.info(f"Inserted subject: {meta.subject_name} → {subject_id}")

    # ── Step 4: Insert chapters → topics → subtopics ─────────────────
    chapters_inserted = 0
    topics_inserted = 0
    subtopics_inserted = 0
    chapter_id_map: dict[int, str] = {}   # chapter_number → chapter UUID
    topic_id_map: dict[str, str] = {}     # "ch_num:topic_name" → topic UUID

    for chapter in extraction.chapters:
        chapter_res = (
            supabase.table("chapters")
            .insert({
                "subject_id": subject_id,
                "name": chapter.name,
                "chapter_number": chapter.chapter_number,
                "description": chapter.description,
                "content": chapter.content,
                "sort_order": chapter.sort_order,
            })
            .execute()
        )
        chapter_id = chapter_res.data[0]["id"]
        chapter_id_map[chapter.chapter_number] = chapter_id
        chapters_inserted += 1

        for topic in chapter.topics:
            topic_res = (
                supabase.table("topics")
                .insert({
                    "chapter_id": chapter_id,
                    "name": topic.name,
                    "description": topic.description,
                    "sort_order": topic.sort_order,
                })
                .execute()
            )
            topic_id = topic_res.data[0]["id"]
            topic_id_map[f"{chapter.chapter_number}:{topic.name}"] = topic_id
            topics_inserted += 1

            if topic.subtopics:
                subtopic_rows = [
                    {
                        "topic_id": topic_id,
                        "name": st.name,
                        "description": st.description,
                        "sort_order": st.sort_order,
                    }
                    for st in topic.subtopics
                ]
                supabase.table("subtopics").insert(subtopic_rows).execute()
                subtopics_inserted += len(subtopic_rows)

    logger.info(
        f"Insertion complete — chapters: {chapters_inserted}, "
        f"topics: {topics_inserted}, subtopics: {subtopics_inserted}"
    )

    # ── Step 5: Insert questions (if provided) ───────────────────
    question_sets_inserted = 0
    questions_inserted = 0

    if questions:
        qs_count, q_count = insert_questions(
            questions, chapter_id_map, topic_id_map
        )
        question_sets_inserted = qs_count
        questions_inserted = q_count

    return InsertResult(
        subject_id=subject_id,
        chapters_inserted=chapters_inserted,
        topics_inserted=topics_inserted,
        subtopics_inserted=subtopics_inserted,
        question_sets_inserted=question_sets_inserted,
        questions_inserted=questions_inserted,
    )


def _question_to_row(q, question_set_id: str) -> dict:
    """Convert a Question model to a database row dict."""
    row = {
        "question_set_id": question_set_id,
        "question_number": q.question_number,
        "question_text": q.question_text,
        "question_type": q.question_type,
        "options": [o.model_dump() for o in q.options] if q.options else None,
        "answer": q.answer,
        "has_image": q.has_image,
        "image_description": q.image_description,
        "image_svg": q.image_svg,
        "difficulty_marker": q.difficulty_marker,
        "sort_order": q.sort_order,
    }
    # Handle sub_questions
    if q.sub_questions:
        row["sub_questions"] = [
            {
                "question_number": sq.question_number,
                "question_text": sq.question_text,
                "question_type": sq.question_type,
                "options": [o.model_dump() for o in sq.options] if sq.options else None,
                "answer": sq.answer,
                "has_image": sq.has_image,
                "image_description": sq.image_description,
                "image_svg": sq.image_svg,
                "difficulty_marker": sq.difficulty_marker,
                "sort_order": sq.sort_order,
            }
            for sq in q.sub_questions
        ]
    else:
        row["sub_questions"] = None
    return row


def _normalize(s: str) -> str:
    """Normalize a string for fuzzy comparison."""
    import re
    return re.sub(r'\s+', ' ', s.strip().lower())


def _fuzzy_find_topic(
    parent_topic_name: str,
    chapter_number: int,
    topic_id_map: dict[str, str],
) -> str | None:
    """
    Find the best matching topic_id for a parent_topic_name.

    Strategy:
    1. Exact match (key = "ch_num:topic_name")
    2. Normalized exact match (case-insensitive, whitespace-normalized)
    3. Substring containment (either direction)
    4. Best overlap by word intersection
    """
    if not parent_topic_name:
        return None

    # 1. Exact match
    exact_key = f"{chapter_number}:{parent_topic_name}"
    if exact_key in topic_id_map:
        return topic_id_map[exact_key]

    # Build candidates for this chapter only
    prefix = f"{chapter_number}:"
    chapter_topics = {
        k: v for k, v in topic_id_map.items() if k.startswith(prefix)
    }
    if not chapter_topics:
        return None

    needle = _normalize(parent_topic_name)

    # 2. Normalized exact match
    for key, tid in chapter_topics.items():
        topic_name = key[len(prefix):]
        if _normalize(topic_name) == needle:
            return tid

    # 3. Substring containment (either direction)
    for key, tid in chapter_topics.items():
        topic_name = _normalize(key[len(prefix):])
        if needle in topic_name or topic_name in needle:
            return tid

    # 4. Best word overlap
    needle_words = set(needle.split())
    best_tid = None
    best_score = 0
    for key, tid in chapter_topics.items():
        topic_name = _normalize(key[len(prefix):])
        topic_words = set(topic_name.split())
        overlap = len(needle_words & topic_words)
        if overlap > best_score and overlap >= 2:
            best_score = overlap
            best_tid = tid

    if best_tid:
        return best_tid

    logger.debug(
        f"No topic match for '{parent_topic_name}' in chapter {chapter_number}. "
        f"Available: {[k[len(prefix):] for k in chapter_topics]}"
    )
    return None


def insert_questions(
    chapter_questions: list[ChapterQuestions],
    chapter_id_map: dict[int, str],
    topic_id_map: dict[str, str],
) -> tuple[int, int]:
    """
    Insert extracted questions into question_sets and questions tables.

    Returns: (question_sets_inserted, questions_inserted)
    """
    sets_count = 0
    qs_count = 0
    matched_topics = 0
    unmatched_topics = 0

    for ch_qs in chapter_questions:
        chapter_id = chapter_id_map.get(ch_qs.chapter_number)
        if not chapter_id:
            logger.warning(
                f"No chapter_id found for chapter {ch_qs.chapter_number}. "
                f"Skipping questions."
            )
            continue

        for qs in ch_qs.question_sets:
            # Fuzzy-match topic_id
            topic_id = _fuzzy_find_topic(
                qs.parent_topic_name, ch_qs.chapter_number, topic_id_map
            )
            if qs.parent_topic_name:
                if topic_id:
                    matched_topics += 1
                else:
                    unmatched_topics += 1

            set_res = (
                supabase.table("question_sets")
                .insert({
                    "chapter_id": chapter_id,
                    "topic_id": topic_id,
                    "name": qs.name,
                    "set_type": qs.set_type,
                    "sort_order": qs.sort_order,
                })
                .execute()
            )
            set_id = set_res.data[0]["id"]
            sets_count += 1

            if qs.questions:
                question_rows = [
                    _question_to_row(q, set_id) for q in qs.questions
                ]
                supabase.table("questions").insert(question_rows).execute()
                qs_count += len(question_rows)

    logger.info(
        f"Questions insertion complete — sets: {sets_count}, questions: {qs_count}, "
        f"topic matches: {matched_topics}/{matched_topics + unmatched_topics}"
    )
    return sets_count, qs_count
