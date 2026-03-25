-- Migration: Add question_sets and questions tables for question extraction feature
-- Run this in Supabase SQL Editor before using the "Extract Questions" toggle.

-- ── Question Sets ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS question_sets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
  topic_id UUID REFERENCES topics(id) ON DELETE SET NULL,
  name TEXT NOT NULL,                    -- "Practice Set 1.1", "Exercise 2.3", etc.
  set_type TEXT NOT NULL DEFAULT 'practice_set',  -- 'practice_set' or 'problem_set'
  sort_order INT NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ── Questions ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS questions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_set_id UUID NOT NULL REFERENCES question_sets(id) ON DELETE CASCADE,
  question_number TEXT NOT NULL,         -- "1", "2", "2.i", "ii"
  question_text TEXT NOT NULL,
  question_type TEXT NOT NULL DEFAULT 'solve',
  sub_questions JSONB,                   -- For compound questions: [{number, text, ...}]
  options JSONB,                         -- MCQ: [{"label":"A","text":"..."},...]
  answer TEXT,
  has_image BOOLEAN DEFAULT false,
  image_description TEXT,
  difficulty_marker TEXT,                -- "★" or null
  marks INT,
  sort_order INT NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ── Row Level Security ───────────────────────────────────────────────────────
ALTER TABLE question_sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read question_sets" ON question_sets FOR SELECT USING (true);
CREATE POLICY "Public read questions" ON questions FOR SELECT USING (true);
CREATE POLICY "Service insert question_sets" ON question_sets FOR INSERT WITH CHECK (true);
CREATE POLICY "Service insert questions" ON questions FOR INSERT WITH CHECK (true);

-- ── Indexes ──────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_question_sets_chapter ON question_sets(chapter_id);
CREATE INDEX IF NOT EXISTS idx_question_sets_topic ON question_sets(topic_id);
CREATE INDEX IF NOT EXISTS idx_questions_set ON questions(question_set_id);
CREATE INDEX IF NOT EXISTS idx_questions_type ON questions(question_type);
