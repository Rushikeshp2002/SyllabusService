"""
Gemini prompt templates for textbook syllabus extraction.

Philosophy:
  The LLM should THINK like a teacher creating a study guide — not like
  an OCR scanner listing every bold word. Every item must be something
  a student would need to study independently.
"""


# ── System context — injected into both passes ───────────────────────────────

SYSTEM_CONTEXT = """
== WHO YOU ARE ==

You are a senior curriculum designer extracting a study-guide structure
from a school textbook. Your output will power an AI tutoring app called
"Sarthi" where students tap on chapters → topics → subtopics and the AI
explains that specific concept to them.

== WHY THIS MATTERS ==

A student will see YOUR output as a clickable syllabus tree:

  📘 [Subject Name]
    📖 Ch 1: [Chapter Title]
      📄 [Topic: a major section heading]
        • [Subtopic: a specific concept worth explaining]
        • [Subtopic: another concept]
      📄 [Topic: next section heading]
        • [Subtopic]
        • [Subtopic]

When they tap on a subtopic, the AI tutor will explain that concept to them.
So every item you extract must be a REAL, STANDALONE LEARNING CONCEPT
that is worth explaining to a student.

== THE DATABASE ==

The following hierarchy is ALREADY in the database (you do NOT extract these):
  Region → Country → Board → Level → Grade → Stream

YOUR job is to extract ONLY:
  Chapters → Topics → Subtopics

These will be inserted under the "Subject" (e.g., the subject name given below).

== DEFINITIONS ==

CHAPTER = A major division of the textbook (Chapter 1, Chapter 2, etc.)
  - Has a number and a name
  - Directly from the Table of Contents

TOPIC = A section within a chapter that covers one learnable area
  - Think of it as: "What is this section trying to teach?"
  - Usually corresponds to numbered headings (1.1, 1.2) or bold section titles
  - Should be something a teacher could give a 15-minute lesson on

SUBTOPIC = A specific concept within a topic that a student needs to understand
  - Think of it as: "What individual concept would a student ask about?"
  - Should be concrete enough for the AI to explain in 2-3 paragraphs
  - NOT: single letters, symbols, page numbers, or exercise instructions
"""


# ── Quality rules — the thinking framework ────────────────────────────────────

QUALITY_RULES = """
== CRITICAL RULE: USE EXACT TEXT FROM THE PDF ==

⚠️  DO NOT INVENT, PARAPHRASE, OR REPHRASE NAMES.

Every topic and subtopic name you extract MUST come from text that is ACTUALLY
PRINTED in the textbook — a section heading, a bold title, a numbered sub-heading,
or a clearly marked concept name.

The user WILL search for every topic/subtopic name in the PDF. If they search and
the EXACT name you gave is NOT found in the PDF, your extraction is WRONG.

EXAMPLES OF WHAT NOT TO DO:
  PDF heading says: "Gravitation"
  WRONG output:     "Newton's Discovery of Gravitation"  ← you invented this!
  RIGHT output:     "Gravitation"                        ← exact PDF text

  PDF heading says: "Circular motion and Centripetal force"
  WRONG output:     "Gravitation and Centripetal Force"   ← you merged/rephrased!
  RIGHT output:     "Circular motion and Centripetal force" ← exact PDF text

  PDF heading says: "Kepler's Laws"
  WRONG output:     "Kepler's Laws of Planetary Motion"   ← you added extra words!
  RIGHT output:     "Kepler's Laws"                       ← exact PDF text

For subtopics: use the EXACT sub-heading, bold text, or concept name as printed.
Do NOT generate descriptive titles. Copy what the book says.

== CRITICAL THINKING RULES ==

Before adding ANY item, ask yourself these questions:

FOR TOPICS:
  ✅ "Could a teacher give a focused lesson on just this section?"
  ✅ "Does this section introduce new concepts that weren't in previous sections?"
  ✅ "Is this name EXACTLY as printed in the PDF?"
  ❌ "Is this just a sub-point of the previous topic?" → merge it
  ❌ "Is this a revision section, exercise, or activity?" → skip it
  ❌ "Did I rephrase or invent this name?" → go back and use the exact PDF text

FOR SUBTOPICS:
  ✅ "Could a student ask 'What is [this]?' and get a meaningful answer?"
  ✅ "Is this a named concept, law, theorem, formula, or principle?"
  ✅ "Would this appear in an exam as a question topic?"
  ✅ "Is this name EXACTLY as printed in the PDF?"
  ❌ "Is this just the topic name repeated?" → skip it
  ❌ "Is this a single word/letter with no meaning on its own?" → skip it
  ❌ "Is this an example, exercise question, or activity?" → skip it
  ❌ "Is this a figure caption, table header, or apparatus name?" → skip it
  ❌ "Is this a chemical formula or element name listed as an example?" → skip it
  ❌ "Did I generate a descriptive title instead of using the PDF text?" → fix it

== ANTI-PATTERNS TO AVOID ==

WRONG: topic name repeated as its own subtopic (e.g., topic "X" → subtopic "X")
WRONG: single-letter or single-word subtopics that mean nothing alone
WRONG: a topic with 0 subtopics (every topic needs at least 1)
WRONG: listing vocabulary words (like element names, apparatus names) as standalone subtopics
       — these should be grouped under the concept they illustrate
WRONG: inventing descriptive topic/subtopic names that don't appear in the PDF
WRONG: paraphrasing or rewording a printed heading into something "better"

RIGHT: topics that represent real, teachable sections from the book
RIGHT: subtopics that are named concepts, laws, principles, or methods
RIGHT: subtopic names that are descriptive enough to explain (3+ words)
RIGHT: ALL names are copied EXACTLY from the textbook headings

== TOPIC CONSOLIDATION ==

If a chapter has many lettered/numbered sub-sections (a, b, c, d, i, ii),
these are probably sub-points of ONE parent topic. MERGE them:

  WRONG (too granular — each sub-point as its own topic):
    topic: "a. [Type one]"
    topic: "b. [Type two]"
    topic: "c. [Type three]"

  RIGHT (consolidated under the parent heading):
    topic: "[Parent heading that contains a, b, c]"
    subtopics: ["[Type one]", "[Type two]", "[Type three]"]

== USE THE INDEX/TOC FIRST ==

Many textbooks — especially engineering, university, and reference books —
have a DETAILED Table of Contents that already lists the full hierarchy:

  Chapter 1: [Chapter Title]
    1.1 [Section Name]
      1.1.1 [Sub-section Name]
      1.1.2 [Sub-section Name]
    1.2 [Section Name]
      1.2.1 [Sub-section Name]
      1.2.2 [Sub-section Name]

If the TOC/index already provides this 3-level structure:
  → Chapter headings = your chapters
  → Section headings (1.1, 1.2) = your topics
  → Sub-section headings (1.1.1, 1.1.2) = your subtopics
  → USE THEM DIRECTLY. Do NOT ignore the printed hierarchy and invent your own.

If the TOC only lists chapter names (common in school textbooks):
  → You must READ the body of each chapter to identify topics and subtopics.

== HANDLING DIFFERENT BOOK TYPES ==

Textbooks vary by education level. Adapt your approach:

SCHOOL (Class 1-10):
  - TOC usually has chapter names only
  - Topics come from numbered section headings in the body (1.1, 1.2)
  - Subtopics are named concepts, laws, definitions within each section

11TH-12TH:
  - TOC may have chapter + section numbers
  - More detailed content — look for numbered sub-headings
  - Subtopics: theorems, derivations, named principles, types/classifications

ENGINEERING / DEGREE (University textbooks):
  - TOC is usually very detailed (3 levels: Chapter → Section → Sub-section)
  - USE the TOC hierarchy directly — it IS your topic/subtopic structure

COMPETITIVE EXAM BOOKS:
  - May be organized by topics rather than traditional chapters
  - Treat major topic groups as chapters
  - Subtopics: problem types, concept variants, formulae

POSTGRADUATE / RESEARCH:
  - Very specialized, dense content
  - Topics map to research areas or methodology steps
  - Subtopics: specific techniques, frameworks, theoretical models

GENERAL RULES for all levels:
  - SCIENCE: laws, principles, definitions, formulas, processes
  - MATHS: theorem names, types of problems, methods — NOT individual exercises
  - SOCIAL SCIENCE: events, concepts, provisions — NOT trivial dates or person names
  - GEOGRAPHY: landforms, processes, climate zones — NOT specific city/location lists

== MINIMUM QUALITY BAR ==

Every topic MUST have at least 1 subtopic.
Every subtopic name MUST be descriptive (3+ words). No single words or abbreviations.
If a subtopic would be meaningless without context, make it self-explanatory.
"""


# ── Descriptive mode rules (language/literature subjects) ─────────────────────

DESCRIPTIVE_RULES = """
== DESCRIPTIVE (LANGUAGE/LITERATURE) SUBJECT MODE ==

This textbook contains stories, poems, essays, dramas — NOT scientific concepts.

⚠️  CRITICAL RULE: DO NOT INVENT OR INTERPRET.

Every topic and subtopic you extract MUST come from text that is ACTUALLY
PRINTED in the textbook. If you cannot point to a specific heading, glossary
entry, exercise title, or activity instruction in the PDF, DO NOT include it.

The review page has a side-by-side PDF viewer. The user WILL click on every
topic/subtopic name and search for it in the PDF. If they can't find it,
your extraction is WRONG.

== HOW TO EXTRACT ==

CHAPTER = a lesson (story, poem, essay, drama extract, etc.)
  - "name" = the title of the piece EXACTLY as printed
  - "description" = MUST be filled (not null). 2-3 sentences:
      Who wrote it? What type is it (poem/story/essay)? What is it about?
  - "content" = the COMPLETE text of the story/poem/essay (verbatim from the book).
      Do NOT include exercises, questions, warming up, or workshop sections.
      For POEMS: include the complete poem text (every stanza, every line).
      For STORIES/ESSAYS: include the FULL story/essay text verbatim.
      Since we extract one chapter at a time, there is no size constraint.

TOPICS — ALWAYS EMPTY for language/literature subjects.
  ALWAYS return "topics": [] — do NOT extract any topics or subtopics.

  This is a language subject where chapters are poems, stories, and essays.
  The chapter's value is captured in the "content" field, not in topics.

  Exercise sections like "Warming Up", "Comprehension", "Workshop",
  "Activities", "Grammar", "Vocabulary" are textbook scaffolding,
  NOT learning content to be extracted as topics.

  IMPORTANT: "topics": [] is the ONLY correct value for this mode.

== DESCRIPTIONS ARE MANDATORY FOR CHAPTERS ==

Every chapter MUST have its "description" field filled (not null).
  - Chapter description: what is this piece about, who wrote it, what type
"""


def build_toc_prompt(subject_name: str, board: str, grade: str, medium: str) -> str:
    return f"""{SYSTEM_CONTEXT}

== YOUR CURRENT TASK: PASS 1 — TABLE OF CONTENTS ==

Textbook: {subject_name} | {board} | {grade} | {medium}

Read the ENTIRE Table of Contents / Index pages of this PDF and extract
the COMPLETE chapter list. You MUST read ALL pages of the TOC — do NOT stop
after the first page or first unit.

Rules:
- Extract EVERY chapter number and EXACT chapter name as printed
- Do NOT include appendices, glossary, index, or answer keys
- Do NOT read the body of the book yet — that's Pass 2
- If the book has "Units" or "Parts" grouping chapters, extract ALL individual
  chapters from EVERY unit (not the group headings). For example:
    Unit One: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6
    Unit Two: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
    Unit Three: 3.1, 3.2, 3.3, ...
    Unit Four: 4.1, 4.2, 4.3, ...
  ALL of these are separate chapters. Extract them ALL.
- Use sequential chapter_number (1, 2, 3, ...) across all units
- If the TOC has a DETAILED structure with sections and sub-sections,
  note that — but still extract only the top-level chapter names here.
  The detailed section/sub-section structure will be used in Pass 2.
- total_chapters must match the number of chapters you found
- COMMON MISTAKE: only reading Unit 1 and stopping. You MUST continue
  through ALL units until you reach the end of the TOC.

Output as JSON matching the schema."""


def build_extraction_prompt(
    subject_name: str,
    board: str,
    grade: str,
    medium: str,
    toc_chapters: list[dict],
    is_descriptive: bool = False,
) -> str:
    toc_list = "\n".join(
        f"  {ch['chapter_number']}. {ch['name']}" for ch in toc_chapters
    )

    rules = DESCRIPTIVE_RULES if is_descriptive else QUALITY_RULES

    # Descriptive subjects need different instructions
    if is_descriptive:
        instructions = """
== INSTRUCTIONS ==

READ THE ENTIRE TEXTBOOK. For each chapter (lesson/poem/story):

1. EXTRACT THE TEXT of the story/poem/essay into the "content" field.
   - POEMS: copy the full poem text verbatim.
   - STORIES/ESSAYS: copy only the first ~500 words (enough for context).
   - Do NOT include exercises or questions in content.
   - This is the MOST IMPORTANT field for language subjects.

2. WRITE A SYNOPSIS in the "description" field (MANDATORY, not null).

3. OPTIONALLY extract topics — ONLY if genuine learning sections exist
   - If the chapter is just a poem/story with no meaningful sections, use "topics": []
   - DO NOT extract exercise scaffolding ("Warming Up", "Comprehension", "Workshop")
   - Only include sections with real learning content (Grammar rules, Vocabulary definitions)
   - If included, use the EXACT heading text as printed"""

        self_check = f"""== SELF-CHECK BEFORE SUBMITTING ==

Before you return the JSON, verify:
  □ Chapter count = {len(toc_chapters)}
  □ Chapter names match the TOC exactly
  □ Every chapter has "content" with the actual story/poem text (not exercises)
  □ Every chapter "description" is filled (NOT null)
  □ Chapters with only a poem/story and no real sections have "topics": []
  □ Any included topics are ACTUAL section headings from the book (not exercise labels)"""
    else:
        instructions = """
== INSTRUCTIONS ==

STEP 1: CHECK THE TABLE OF CONTENTS / INDEX FIRST.

If the TOC already has a detailed structure like:
  Chapter 1: [Title]
    1.1 [Section name]
      1.1.1 [Sub-section name]
      1.1.2 [Sub-section name]
    1.2 [Section name]

Then USE IT:
  - Section headings (1.1, 1.2) → your topics
  - Sub-section headings (1.1.1, 1.1.2) → your subtopics
  - Do NOT ignore this and invent your own structure
  - Use the EXACT text of each heading as the topic/subtopic name

STEP 2: If the TOC only lists chapter names with bullet-point topics:
  - The TOC topic names ARE your topic names. Use them EXACTLY.
  - Then READ the body of each chapter to find subtopics.

STEP 3: If the TOC only lists chapter names with NO topics:
  READ THE BODY of each chapter:

1. IDENTIFY THE MAIN SECTIONS (topics)
   - Look at numbered headings (1.1, 1.2, etc.) or bold section titles
   - USE THE EXACT HEADING TEXT as the topic name — do NOT rephrase
   - Consolidate sub-points (a, b, c, d) under their parent heading
   - Each topic should represent one "lesson" a teacher could teach

2. IDENTIFY KEY CONCEPTS WITHIN EACH SECTION (subtopics)
   - Look for sub-headings, bold terms, or named concepts IN THE TEXT
   - USE THE EXACT TEXT from the book — do NOT invent descriptive names
   - If a sub-heading says "Circular motion and Centripetal force", use EXACTLY that
   - Do NOT rephrase it as "Understanding Centripetal Force in Circular Motion"
   - Aim for 2-6 subtopics per topic

3. WRITE A SHORT DESCRIPTION for each chapter, topic, and subtopic
   - Descriptions CAN be your own words (summaries are fine)
   - But the NAME fields must be exact PDF text"""

        self_check = f"""== SELF-CHECK BEFORE SUBMITTING ==

Before you return the JSON, verify:
  □ Chapter count = {len(toc_chapters)}
  □ Chapter names match the TOC exactly
  □ EVERY topic name is EXACTLY as printed in the PDF (not rephrased)
  □ EVERY subtopic name is EXACTLY as printed in the PDF (not invented)
  □ If you search for any topic/subtopic name in the PDF, you WILL find it
  □ No topic has 0 subtopics
  □ No subtopic name is just repeating its parent topic name
  □ No subtopic is a single word or abbreviation
  □ Small sub-sections (a, b, c, i, ii) are merged under parent topics
  □ No exercise questions, activities, or "Do you know?" boxes included
  □ Every subtopic passes the test: "Could a student ask 'Explain [this]'?\""""

    return f"""{SYSTEM_CONTEXT}

{rules}

== YOUR CURRENT TASK: PASS 2 — FULL STRUCTURE EXTRACTION ==

Textbook: {subject_name} | {board} | {grade} | {medium}
{'(DESCRIPTIVE/LANGUAGE MODE — extract full story text)' if is_descriptive else ''}

Chapter list from Pass 1 ({len(toc_chapters)} chapters):
{toc_list}

{instructions}

{self_check}

Output as JSON matching the schema."""


def build_single_chapter_prompt(
    subject_name: str,
    board: str,
    grade: str,
    medium: str,
    chapter_number: int,
    chapter_name: str,
) -> str:
    """
    Prompt for extracting a SINGLE chapter in descriptive mode.

    Used by the chapter-by-chapter extraction loop to keep each request
    well within token limits (one chapter at a time instead of all 24+).
    """
    return f"""{SYSTEM_CONTEXT}

{DESCRIPTIVE_RULES}

== YOUR CURRENT TASK: SINGLE CHAPTER EXTRACTION ==

Textbook: {subject_name} | {board} | {grade} | {medium}
(DESCRIPTIVE/LANGUAGE MODE — extract full story/poem text)

Extract ONLY this ONE chapter:
  Chapter {chapter_number}: {chapter_name}

== INSTRUCTIONS ==

Find Chapter {chapter_number} ("{chapter_name}") in the PDF and extract:

1. CHAPTER METADATA
   - chapter_number: {chapter_number}
   - name: "{chapter_name}" (exact title as printed — correct any OCR errors)
   - sort_order: {chapter_number}
   - description: MANDATORY (not null). 2-3 sentences. Who wrote it? What type (poem/story/essay)? What is it about?

2. CONTENT (the actual text — COMPLETE, not truncated)
   - If POEM: copy the complete poem text verbatim (every stanza, every line)
   - If STORY or ESSAY: copy the FULL text verbatim (do NOT truncate or summarize)
   - Do NOT include exercises, questions, "Warming Up", or "Workshop" sections in content

3. TOPICS — SET TO EMPTY: "topics": []
   - This is a LANGUAGE/LITERATURE subject. Chapters are poems, stories, and essays.
   - ALWAYS use "topics": [] — do NOT extract any topics or subtopics.
   - Exercise sections like "Warming Up", "Comprehension", "Workshop", "Activities" are NOT topics.
   - The content field captures the chapter's value. Topics are not needed.

== OUTPUT FORMAT ==

Return a JSON object for THIS ONE CHAPTER ONLY matching the SingleChapterExtraction schema.
Do NOT wrap it in a "chapters" array — return the chapter object directly.

Output as JSON matching the schema."""


# ── Question extraction rules (Pass 3) ────────────────────────────────────────

QUESTION_EXTRACTION_RULES = """
== QUESTION EXTRACTION MODE ==

You are extracting ALL questions and problems from a single chapter of a
textbook. The output will be stored in a question bank for student practice.

== HOW TO FIND QUESTION SETS ==

A "question set" is any NAMED GROUP of questions in the textbook. These are
typically labeled with headings like exercises, practice sets, problem sets,
review questions, worksheets, etc. — but the exact naming varies by textbook.

DO NOT assume any specific naming pattern. Find them by looking for:
  - Headings that introduce a numbered list of questions/problems
  - Sections explicitly labeled as exercises, problems, questions, etc.
  - End-of-chapter or end-of-topic question collections

For each question set you find:
  - "name" = the EXACT heading as printed (e.g. "Exercise 2.3", "Problem Set - 1")
  - "set_type" = "practice_set" if it appears within/after a topic section,
                 "problem_set" if it is a comprehensive set at the end of the chapter
  - "parent_topic_name" = the topic/section heading this set falls under
                          (null if it's a chapter-level comprehensive set)

== HOW TO EXTRACT QUESTIONS ==

For EVERY question in each set, extract:

  question_number: as printed (1, 2, 3, i, ii, (1), (2), etc.)
  question_text: the FULL question text, verbatim
  question_type: classify based on content:
    - "mcq" → multiple choice with labeled options
    - "fill_blank" → fill in the blanks
    - "solve" → solve an equation or compute a value
    - "word_problem" → real-world scenario requiring setup + solve
    - "true_false" → true/false or agree/disagree
    - "match" → match columns or pairs
    - "short_answer" → brief answer or explanation expected
    - "draw" → draw a graph, diagram, or figure
    - "complete_table" → fill in a table with values
    - "complete_activity" → complete a flowchart, activity, or guided solution

  sub_questions: if the question has numbered sub-parts like (1), (2), (3)
    or (i), (ii) under it, extract each sub-part as a nested question.
    Use this for compound questions ONLY.

  options: for MCQ questions only — list all options with labels
    e.g. [{"label": "A", "text": "..."}, {"label": "B", "text": "..."}]

  answer: look in the ANSWER KEY or ANSWERS section (usually at the back
    of the book) and match the answer to this question. If no answer key
    exists or the answer is not found, set to null.

  has_image: true if the question includes, references, or requires a
    diagram, graph, figure, chart, or illustration
  image_description: if has_image is true, describe the visual with EXACT
    mathematical precision. Include ALL of the following that apply:
    - For coordinate graphs: axis ranges (e.g. X: -5 to 8, Y: -3 to 6),
      scale (e.g. 1cm = 1 unit), every plotted point with exact coordinates
      like (-4,4), (-2,3), (0,2), (2,1), every line/curve with its equation
      (e.g. x + 2y = 4), labels on axes and points
    - For geometric figures: vertex labels, side lengths, angle measures,
      parallel/perpendicular markings, altitude/median lines
    - For number lines: range, marked points, intervals
    - For bar/pie charts: category labels, exact values
    - For Venn diagrams: set labels, elements in each region
    Write as structured data, not prose. Example:
    "Coordinate plane. X-axis: -5 to 9, Y-axis: -3 to 6, scale 1cm=1 unit.
     Line 1: x + 2y = 4 (red), passes through (-4,4), (-2,3), (0,2), (2,1).
     Line 2: 3x + 6y = 12 (blue), same line. Both equations represent the
     same single line."
  image_svg: if has_image is true AND the image is a geometric/mathematical
    diagram (coordinate plane, graph, triangle, number line, Venn diagram,
    bar chart), generate a precise SVG following these rules:
    - viewBox="0 0 400 300", origin at pixel (200,150)
    - COMPUTE exact pixel positions: px_x = 200 + x * scale, px_y = 150 - y * scale
      where scale = pixels_per_unit based on axis range
    - Axes: lines with arrow tips, tick marks every 1 unit, small numeric labels
    - Points: <circle> at computed positions, labeled with coordinates
    - Lines: compute two points from the equation, draw <line> between them
    - Colors: #e74c3c red, #2563eb blue, #16a34a green, #ea580c orange
    - Text: font-family="sans-serif", font-size 10-12
    - White background <rect>, no CSS classes, inline styles only
    - Output complete <svg>...</svg> string
    - Set null if the image is a photograph or complex illustration

  difficulty_marker: if the question is marked with a star (★), asterisk (*),
    or any other difficulty indicator, capture that marker. Otherwise null.

== MATHEMATICAL EXPRESSIONS ==

Use plain text with standard notation:
  - Superscripts: x^2, x^n, a^(m+n)
  - Subscripts: a₁, a₂ or a_1, a_2
  - Fractions: a/b, (a+b)/(c+d)
  - Square root: √2, √(a+b)
  - Symbols: ≤, ≥, ≠, ∈, ∑, π, ∞, ∴, ∵
  - Matrices/determinants: describe as |a b; c d| or use row notation

== CRITICAL RULES ==

1. Extract EVERY question — do NOT skip any, even if they seem trivial
2. Use EXACT text from the book — do NOT paraphrase questions
3. Maintain the original numbering scheme
4. If a question is partially visible or unclear, extract what you can
   and note the issue in image_description
5. Do NOT extract worked examples or solved illustrations — only questions
   that students are expected to solve
6. Activities where students fill in blanks as part of learning ARE questions
"""


def build_question_extraction_prompt(
    subject_name: str,
    board: str,
    grade: str,
    medium: str,
    chapter_number: int,
    chapter_name: str,
) -> str:
    """
    Prompt for extracting ALL questions from a SINGLE chapter.

    Used by the per-chapter question extraction loop (Pass 3).
    Generic — works for any subject, any board.
    """
    return f"""{SYSTEM_CONTEXT}

{QUESTION_EXTRACTION_RULES}

== YOUR CURRENT TASK: EXTRACT QUESTIONS FROM ONE CHAPTER ==

Textbook: {subject_name} | {board} | {grade} | {medium}

Extract ALL questions from ONLY this chapter:
  Chapter {chapter_number}: {chapter_name}

== INSTRUCTIONS ==

1. Find Chapter {chapter_number} ("{chapter_name}") in the PDF.

2. Scan through the ENTIRE chapter and identify ALL question sets
   (any named groups of questions/exercises/problems).

3. For each question set, extract EVERY question with full details.

4. Check the ANSWER KEY / ANSWERS section at the BACK of the book:
   - Look for answers corresponding to this chapter's question sets
   - Match answers to their respective questions by number
   - If answers exist, fill in the "answer" field

5. Return the result as a ChapterQuestions object:
   - chapter_number: {chapter_number}
   - chapter_name: "{chapter_name}"
   - question_sets: list of all question sets found in this chapter

== SELF-CHECK ==

Before submitting, verify:
  □ You found ALL question sets in this chapter (not just the first one)
  □ You extracted EVERY question from each set (not just a sample)
  □ Questions with sub-parts have sub_questions filled
  □ MCQ questions have options filled with all choices
  □ Answers from the answer key are matched correctly
  □ Graph/diagram questions have has_image=true and image_description
  □ Question numbers match what's printed in the book
  □ sort_order values are sequential within each set

Output as JSON matching the schema."""
