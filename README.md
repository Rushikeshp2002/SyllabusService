# SyllabusService

Standalone tool to ingest Maharashtra Board (and other Indian board) textbook PDFs into Sarthi's Supabase database.

## How it works
1. Upload a PDF textbook + metadata (board, grade, medium, subject)
2. Gemini 1.5 Pro reads the full PDF natively (no OCR needed)
3. Two-pass strategy: TOC extraction → Full hierarchy extraction
4. Review the JSON tree in-browser, edit if needed
5. Approve → data inserted into Supabase

## Setup

```bash
cd backend
pip install -r requirements.txt
```

The `.env` file at the root already has all credentials.

## Run

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Then open: **http://localhost:8000**

## Project Structure

```
SyllabusService/
  frontend/
    index.html      ← Upload form
    review.html     ← Review & approve
    style.css
  backend/
    main.py         ← FastAPI app
    config.py       ← Env/config loader
    models.py       ← Pydantic schemas
    prompt.py       ← Gemini prompts
    gemini_service.py ← Files API + extraction
    validator.py    ← TOC cross-check
    inserter.py     ← Supabase insertion
    requirements.txt
  reference/
    syllabus_database_design.md
  .env              ← API keys (do not commit)
```

## Textbooks (already available)

All in `../Syllabus/10th/StateBoard/Maharashtra/English/`:
- English.pdf
- Geography.pdf
- Hindi.pdf
- HistoryAndPoliticalScience.pdf
- Marathi.pdf
- Mathematics1.pdf  ← Start with this (smallest, 5 MB)
- Mathematics2.pdf
- ScienceAndTechnologyPart1.pdf
- ScienceAndTechnologyPart2.pdf

## Notes
- Free Gemini tier: 50 requests/day. Each book = 2 requests. All 9 books = 18 requests.
- Uploaded files are auto-deleted from Gemini after 48 hours.
- The inserter uses the `service_role` key (bypasses RLS). Make sure base seed data exists first.
