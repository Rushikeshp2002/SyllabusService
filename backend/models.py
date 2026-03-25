from pydantic import BaseModel, Field
from typing import List, Optional


# ── Extraction output (what Gemini returns) ──────────────────────────────────

class Subtopic(BaseModel):
    name: str = Field(description="Exact subtopic name as printed in the textbook")
    description: Optional[str] = Field(default=None, description="Brief concept summary for AI tutor context")
    sort_order: int = Field(description="1-based order within parent topic")


class Topic(BaseModel):
    name: str = Field(description="Topic/section name within the chapter")
    description: Optional[str] = Field(default=None, description="Section summary")
    sort_order: int = Field(description="1-based order within parent chapter")
    subtopics: List[Subtopic] = Field(default=[], description="All subtopics within this topic")


class Chapter(BaseModel):
    chapter_number: int = Field(description="The chapter number as printed (1, 2, 3...)")
    name: str = Field(description="Full chapter name exactly as printed in the book")
    description: Optional[str] = Field(
        default=None,
        description="One-line summary from the chapter's introduction or first paragraph"
    )
    content: Optional[str] = Field(
        default=None,
        description="Full story/poem/essay text for descriptive (language) subjects. NULL for science/math."
    )
    sort_order: int = Field(description="Same as chapter_number usually")
    topics: List[Topic] = Field(default=[], description="All topics/sections within this chapter")


class ExtractionMetadata(BaseModel):
    total_chapters_found: int = Field(description="Total number of chapters extracted")
    confidence: str = Field(
        description="'high' if structure was clear, 'medium' if some ambiguity, 'low' if structure was unclear"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Any observations about ambiguous structure, unusual formatting, etc."
    )


class TextbookExtraction(BaseModel):
    metadata: ExtractionMetadata
    chapters: List[Chapter]


# ── Single-chapter extraction (for descriptive/language subjects) ─────────────
# Descriptive mode extracts one chapter at a time to avoid token overflow.

class SingleChapterExtraction(BaseModel):
    chapter_number: int = Field(description="The chapter number as printed")
    name: str = Field(description="Full chapter name exactly as printed")
    description: str = Field(
        description="MANDATORY. 2-3 sentence synopsis: author, type, what it's about"
    )
    content: Optional[str] = Field(
        default=None,
        description="Full text of the poem/story/essay verbatim from the book."
    )
    sort_order: int = Field(description="Same as chapter_number")
    topics: List[Topic] = Field(default=[], description="ALWAYS empty for descriptive mode")


# ── Question extraction (Pass 3) ─────────────────────────────────────────────

class QuestionOption(BaseModel):
    label: str = Field(description="Option label as printed: A, B, C, D, etc.")
    text: str = Field(description="Option text")


class Question(BaseModel):
    question_number: str = Field(description="Question number as printed: 1, 2, i, ii, 2.i, etc.")
    question_text: str = Field(description="Full question text verbatim")
    question_type: str = Field(
        description="Classify as: mcq | fill_blank | solve | word_problem | true_false | match | short_answer | draw | complete_table | complete_activity"
    )
    sub_questions: Optional[List['Question']] = Field(
        default=None,
        description="Sub-parts of this question, e.g. (1), (2), (3) under a main question"
    )
    options: Optional[List[QuestionOption]] = Field(default=None, description="MCQ options only")
    answer: Optional[str] = Field(default=None, description="Answer from the answer key section")
    has_image: bool = Field(default=False, description="True if question contains/references an image, graph, or diagram")
    image_description: Optional[str] = Field(
        default=None,
        description="Textual description of the image/graph/diagram if present"
    )
    image_svg: Optional[str] = Field(
        default=None,
        description="SVG diagram string for geometric/mathematical diagrams (coordinate planes, triangles, graphs, etc.)"
    )
    difficulty_marker: Optional[str] = Field(default=None, description="Star marker if present, e.g. ★")
    sort_order: int = Field(description="Order within the question set")


class QuestionSet(BaseModel):
    name: str = Field(description="Set name as printed in the book, e.g. 'Practice Set 1.1', 'Exercise 2.3'")
    set_type: str = Field(description="'practice_set' for mid-chapter sets, 'problem_set' for end-of-chapter comprehensive sets")
    parent_topic_name: Optional[str] = Field(
        default=None,
        description="Name of the topic/section this set belongs to (null for chapter-level problem sets)"
    )
    sort_order: int
    questions: List[Question]


class ChapterQuestions(BaseModel):
    chapter_number: int = Field(description="Chapter number as printed")
    chapter_name: str = Field(description="Chapter name as printed")
    question_sets: List[QuestionSet]



# ── TOC-only pass (Pass 1) ───────────────────────────────────────────────────

class TOCChapter(BaseModel):
    chapter_number: int
    name: str


class TOCExtraction(BaseModel):
    total_chapters: int
    chapters: List[TOCChapter]


# ── API request/response models ──────────────────────────────────────────────

class UploadMetadata(BaseModel):
    """Metadata from the upload form. Uses human-readable names for Gemini prompts,
    and UUIDs for direct Supabase insertion."""

    # Human-readable (used in Gemini prompt)
    region: str = "Asia"
    country: str = "India"
    board: str = "Maharashtra State Board"
    grade: str = "Class 10"
    stream: str = "General"
    medium: str = "English"
    medium_code: str = "en"
    subject_name: str
    is_descriptive: bool = False   # True for language/literature subjects
    extract_questions: bool = False  # True to extract questions/problems from the book

    # UUIDs resolved from frontend cascade (used by inserter)
    # These come from the cascading dropdowns that query Supabase
    education_system_id: Optional[str] = None
    education_level_id: Optional[str] = None
    grade_id: Optional[str] = None
    stream_id: Optional[str] = None


class JobStatus(BaseModel):
    job_id: str
    status: str           # "pending" | "processing" | "done" | "error"
    progress: str         # Human-readable status message
    warning: Optional[str] = None
    error: Optional[str] = None


class JobResult(BaseModel):
    job_id: str
    metadata: UploadMetadata
    extraction: TextbookExtraction
    toc_chapters: List[TOCChapter]
    validation_warning: Optional[str] = None
    questions: Optional[List[ChapterQuestions]] = None


class InsertRequest(BaseModel):
    job_id: str
    extraction: TextbookExtraction   # Possibly edited by user in review UI
    metadata: UploadMetadata
    questions: Optional[List[ChapterQuestions]] = None


class InsertResult(BaseModel):
    subject_id: str
    chapters_inserted: int
    topics_inserted: int
    subtopics_inserted: int
    question_sets_inserted: int = 0
    questions_inserted: int = 0
