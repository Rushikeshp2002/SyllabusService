-- ============================================================
-- SCHEMA MIGRATION: Add medium columns to subjects table
-- Run this BEFORE the seed.sql if the columns don't exist yet
-- ============================================================

-- Add medium columns (safe to re-run)
ALTER TABLE subjects ADD COLUMN IF NOT EXISTS medium TEXT;
ALTER TABLE subjects ADD COLUMN IF NOT EXISTS medium_code TEXT DEFAULT 'en';

-- Add medium_code to user_curriculum_enrollments (for future use)
ALTER TABLE user_curriculum_enrollments ADD COLUMN IF NOT EXISTS medium_code TEXT DEFAULT 'en';
