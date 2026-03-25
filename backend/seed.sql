-- ============================================================
-- SARTHI SYLLABUS — COMPLETE DATABASE SEED
-- ============================================================
-- Source: global_education_catalog.md + syllabus_database_design.md
-- Seeds: regions → countries → education_systems → education_levels → grades → streams
-- Does NOT seed: subjects, chapters, topics, subtopics (from SyllabusService pipeline)
-- ============================================================

-- ============================================================
-- 1. REGIONS (7)
-- ============================================================
INSERT INTO regions (name, code, sort_order) VALUES
  ('Asia',          'AS', 1),
  ('Europe',        'EU', 2),
  ('North America', 'NA', 3),
  ('South America', 'SA', 4),
  ('Africa',        'AF', 5),
  ('Oceania',       'OC', 6),
  ('Middle East',   'ME', 7)
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- 2. COUNTRIES (37)
-- ============================================================
INSERT INTO countries (region_id, name, iso_code, flag_emoji, is_active, sort_order) VALUES
  ((SELECT id FROM regions WHERE code='AS'), 'India',       'IN', '🇮🇳', true, 1),
  ((SELECT id FROM regions WHERE code='AS'), 'China',       'CN', '🇨🇳', true, 2),
  ((SELECT id FROM regions WHERE code='AS'), 'Japan',       'JP', '🇯🇵', true, 3),
  ((SELECT id FROM regions WHERE code='AS'), 'South Korea', 'KR', '🇰🇷', true, 4),
  ((SELECT id FROM regions WHERE code='AS'), 'Singapore',   'SG', '🇸🇬', true, 5),
  ((SELECT id FROM regions WHERE code='AS'), 'Malaysia',    'MY', '🇲🇾', true, 6),
  ((SELECT id FROM regions WHERE code='AS'), 'Indonesia',   'ID', '🇮🇩', true, 7),
  ((SELECT id FROM regions WHERE code='AS'), 'Thailand',    'TH', '🇹🇭', true, 8),
  ((SELECT id FROM regions WHERE code='AS'), 'Philippines', 'PH', '🇵🇭', true, 9),
  ((SELECT id FROM regions WHERE code='AS'), 'Vietnam',     'VN', '🇻🇳', true, 10)
ON CONFLICT (iso_code) DO NOTHING;

INSERT INTO countries (region_id, name, iso_code, flag_emoji, is_active, sort_order) VALUES
  ((SELECT id FROM regions WHERE code='EU'), 'United Kingdom', 'GB', '🇬🇧', true, 1),
  ((SELECT id FROM regions WHERE code='EU'), 'France',         'FR', '🇫🇷', true, 2),
  ((SELECT id FROM regions WHERE code='EU'), 'Germany',        'DE', '🇩🇪', true, 3),
  ((SELECT id FROM regions WHERE code='EU'), 'Spain',          'ES', '🇪🇸', true, 4),
  ((SELECT id FROM regions WHERE code='EU'), 'Italy',          'IT', '🇮🇹', true, 5),
  ((SELECT id FROM regions WHERE code='EU'), 'Netherlands',    'NL', '🇳🇱', true, 6),
  ((SELECT id FROM regions WHERE code='EU'), 'Russia',         'RU', '🇷🇺', true, 7),
  ((SELECT id FROM regions WHERE code='EU'), 'Finland',        'FI', '🇫🇮', true, 8),
  ((SELECT id FROM regions WHERE code='EU'), 'Sweden',         'SE', '🇸🇪', true, 9),
  ((SELECT id FROM regions WHERE code='EU'), 'Poland',         'PL', '🇵🇱', true, 10)
ON CONFLICT (iso_code) DO NOTHING;

INSERT INTO countries (region_id, name, iso_code, flag_emoji, is_active, sort_order) VALUES
  ((SELECT id FROM regions WHERE code='NA'), 'United States', 'US', '🇺🇸', true, 1),
  ((SELECT id FROM regions WHERE code='NA'), 'Canada',        'CA', '🇨🇦', true, 2),
  ((SELECT id FROM regions WHERE code='NA'), 'Mexico',        'MX', '🇲🇽', true, 3)
ON CONFLICT (iso_code) DO NOTHING;

INSERT INTO countries (region_id, name, iso_code, flag_emoji, is_active, sort_order) VALUES
  ((SELECT id FROM regions WHERE code='SA'), 'Brazil',    'BR', '🇧🇷', true, 1),
  ((SELECT id FROM regions WHERE code='SA'), 'Argentina', 'AR', '🇦🇷', true, 2),
  ((SELECT id FROM regions WHERE code='SA'), 'Colombia',  'CO', '🇨🇴', true, 3),
  ((SELECT id FROM regions WHERE code='SA'), 'Chile',     'CL', '🇨🇱', true, 4),
  ((SELECT id FROM regions WHERE code='SA'), 'Peru',      'PE', '🇵🇪', true, 5)
ON CONFLICT (iso_code) DO NOTHING;

INSERT INTO countries (region_id, name, iso_code, flag_emoji, is_active, sort_order) VALUES
  ((SELECT id FROM regions WHERE code='AF'), 'South Africa', 'ZA', '🇿🇦', true, 1),
  ((SELECT id FROM regions WHERE code='AF'), 'Nigeria',      'NG', '🇳🇬', true, 2),
  ((SELECT id FROM regions WHERE code='AF'), 'Kenya',        'KE', '🇰🇪', true, 3),
  ((SELECT id FROM regions WHERE code='AF'), 'Ghana',        'GH', '🇬🇭', true, 4),
  ((SELECT id FROM regions WHERE code='AF'), 'Egypt',        'EG', '🇪🇬', true, 5),
  ((SELECT id FROM regions WHERE code='AF'), 'Ethiopia',     'ET', '🇪🇹', true, 6),
  ((SELECT id FROM regions WHERE code='AF'), 'Tanzania',     'TZ', '🇹🇿', true, 7)
ON CONFLICT (iso_code) DO NOTHING;

INSERT INTO countries (region_id, name, iso_code, flag_emoji, is_active, sort_order) VALUES
  ((SELECT id FROM regions WHERE code='OC'), 'Australia',   'AU', '🇦🇺', true, 1),
  ((SELECT id FROM regions WHERE code='OC'), 'New Zealand', 'NZ', '🇳🇿', true, 2)
ON CONFLICT (iso_code) DO NOTHING;

INSERT INTO countries (region_id, name, iso_code, flag_emoji, is_active, sort_order) VALUES
  ((SELECT id FROM regions WHERE code='ME'), 'UAE',          'AE', '🇦🇪', true, 1),
  ((SELECT id FROM regions WHERE code='ME'), 'Saudi Arabia', 'SA', '🇸🇦', true, 2),
  ((SELECT id FROM regions WHERE code='ME'), 'Qatar',        'QA', '🇶🇦', true, 3),
  ((SELECT id FROM regions WHERE code='ME'), 'Oman',         'OM', '🇴🇲', true, 4),
  ((SELECT id FROM regions WHERE code='ME'), 'Turkey',       'TR', '🇹🇷', true, 5)
ON CONFLICT (iso_code) DO NOTHING;

-- ============================================================
-- 3. EDUCATION SYSTEMS
-- ============================================================

-- India — National Boards
INSERT INTO education_systems (country_id, name, short_name, system_type, description, is_active, sort_order) VALUES
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Central Board of Secondary Education', 'CBSE', 'national_board', '27,000+ schools. NCERT textbooks.', true, 1),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Council for the Indian School Certificate Examinations', 'ICSE', 'private_board', '2,750+ schools. ICSE/ISC exams.', true, 2),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'National Institute of Open Schooling', 'NIOS', 'national_board', 'Flexible/distance schooling.', true, 3);

-- India — ALL State Boards (28 states from catalog)
INSERT INTO education_systems (country_id, name, short_name, system_type, description, is_active, sort_order) VALUES
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Board of Secondary Education, Andhra Pradesh',                     'BSEAP',     'state_board', 'SSC + Intermediate (BIEAP)',              true, 10),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Board of Secondary Education, Assam',                              'SEBA',      'state_board', 'HSLC + Higher Secondary (AHSEC)',         true, 11),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Bihar School Examination Board',                                    'BSEB',      'state_board', 'Matric + Intermediate',                   true, 12),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Chhattisgarh Board of Secondary Education',                         'CGBSE',     'state_board', 'Class 10 + Class 12',                     true, 13),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Goa Board of Secondary & Higher Secondary Education',               'GBSHSE',    'state_board', 'SSC + HSSC',                              true, 14),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Gujarat Secondary & Higher Secondary Education Board',              'GSHSEB',    'state_board', 'SSC + HSC',                               true, 15),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Board of School Education, Haryana',                                'BSEH',      'state_board', 'Class 10 + Class 12',                     true, 16),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Himachal Pradesh Board of School Education',                        'HPBOSE',    'state_board', 'Matric + Plus Two',                       true, 17),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'J&K Board of School Education',                                     'JKBOSE',    'state_board', 'Class 10 + Class 12',                     true, 18),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Jharkhand Academic Council',                                        'JAC',       'state_board', 'Class 10 + Intermediate',                 true, 19),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Karnataka Secondary Education Examination Board',                   'KSEEB',     'state_board', 'SSLC + PUC (DPUE)',                       true, 20),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Kerala Board of Public Examinations',                               'KBPE',      'state_board', 'SSLC + Higher Secondary',                 true, 21),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Madhya Pradesh Board of Secondary Education',                       'MPBSE',     'state_board', 'Class 10 + Class 12',                     true, 22),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Maharashtra State Board of Secondary & Higher Secondary Education', 'MSBSHSE',   'state_board', 'SSC (Class 10) + HSC (Class 12)',         true, 23),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Board of Secondary Education, Manipur',                             'BOSEM',     'state_board', 'HSLC + Higher Secondary (COHSEM)',        true, 24),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Meghalaya Board of School Education',                               'MBOSE',     'state_board', 'SSLC + HSSLC',                            true, 25),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Mizoram Board of School Education',                                 'MBSE',      'state_board', 'HSLC + HSSLC',                            true, 26),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Nagaland Board of School Education',                                'NBSE',      'state_board', 'HSLC + HSSLC',                            true, 27),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Board of Secondary Education, Odisha',                              'BSE_ODISHA','state_board', 'HSC + CHSE Higher Secondary',             true, 28),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Punjab School Education Board',                                     'PSEB',      'state_board', 'Matric + Plus Two',                       true, 29),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Board of Secondary Education, Rajasthan',                           'RBSE',      'state_board', 'Class 10 + Class 12',                     true, 30),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Sikkim Board of Secondary Education',                               'SBSE',      'state_board', 'Class 10 + Class 12',                     true, 31),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Tamil Nadu State Board of School Examinations',                     'TNSBSE',    'state_board', 'SSLC + HSC',                              true, 32),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Board of Secondary Education, Telangana',                           'BSET',      'state_board', 'SSC + Intermediate (TSBIE)',              true, 33),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Tripura Board of Secondary Education',                              'TBSE',      'state_board', 'Madhyamik + Higher Secondary',            true, 34),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Uttar Pradesh Madhyamik Shiksha Parishad',                          'UPMSP',     'state_board', 'High School + Intermediate',              true, 35),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Uttarakhand Board of School Education',                             'UBSE',      'state_board', 'Class 10 + Class 12',                     true, 36),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'West Bengal Board of Secondary Education',                          'WBBSE',     'state_board', 'Madhyamik + Higher Secondary (WBCHSE)',   true, 37);

-- India — Competitive Exams
INSERT INTO education_systems (country_id, name, short_name, system_type, description, is_active, sort_order) VALUES
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Joint Entrance Examination',           'JEE',  'competitive_exam', 'IIT/NIT Engineering entrance.',  true, 50),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'National Eligibility cum Entrance Test','NEET', 'competitive_exam', 'Medical (MBBS/BDS) entrance.',   true, 51),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Union Public Service Commission',      'UPSC', 'competitive_exam', 'Civil Services (IAS/IPS/IFS).',  true, 52),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Common Admission Test',                'CAT',  'competitive_exam', 'MBA admission to IIMs.',         true, 53),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Graduate Aptitude Test in Engineering', 'GATE', 'competitive_exam', 'M.Tech + PSU entrance.',         true, 54),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Common Law Admission Test',            'CLAT', 'competitive_exam', 'National Law University.',       true, 55),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'National Defence Academy Entrance',    'NDA',  'competitive_exam', 'Defense Forces entrance.',       true, 56),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'SSC Combined Graduate Level',          'SSC_CGL','competitive_exam','Government Jobs exam.',          true, 57),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'IBPS / SBI Banking Exams',             'IBPS', 'competitive_exam', 'Bank recruitment exams.',         true, 58),
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Common University Entrance Test',      'CUET', 'competitive_exam', 'Central University admissions.',  true, 59);

-- India — Higher Education
INSERT INTO education_systems (country_id, name, short_name, system_type, description, is_active, sort_order) VALUES
  ((SELECT id FROM countries WHERE iso_code='IN'), 'Indian University System', 'IN_UNIV', 'university', 'B.Tech, B.Sc, B.Com, B.A., MBBS, BBA, LLB, etc.', true, 60);

-- United States
INSERT INTO education_systems (country_id, name, short_name, system_type, description, is_active, sort_order) VALUES
  ((SELECT id FROM countries WHERE iso_code='US'), 'US K-12 Education',  'US_K12', 'national_board', 'Elementary → Middle → High School.', true, 1),
  ((SELECT id FROM countries WHERE iso_code='US'), 'Advanced Placement', 'AP',     'national_board', 'College Board. 38+ AP subjects.',    true, 2);

-- United Kingdom
INSERT INTO education_systems (country_id, name, short_name, system_type, description, is_active, sort_order) VALUES
  ((SELECT id FROM countries WHERE iso_code='GB'), 'England & Wales National Curriculum',   'UK_NC', 'national_board', 'Key Stages 1-5, GCSE + A-Level.', true, 1),
  ((SELECT id FROM countries WHERE iso_code='GB'), 'Scottish Qualifications Authority',     'SQA',   'national_board', 'Nationals → Highers → Adv Highers.', true, 2);

-- International (country_id = NULL)
INSERT INTO education_systems (country_id, name, short_name, system_type, description, is_active, sort_order) VALUES
  (NULL, 'International Baccalaureate',                   'IB',   'international_curriculum', 'PYP → MYP → DP. 6 subject groups.', true, 1),
  (NULL, 'Cambridge Assessment International Education',  'CAIE', 'international_curriculum', 'IGCSE + AS & A Level. 70+ subjects.', true, 2);

-- Australia, New Zealand, Canada
INSERT INTO education_systems (country_id, name, short_name, system_type, description, is_active, sort_order) VALUES
  ((SELECT id FROM countries WHERE iso_code='AU'), 'Australian Curriculum',        'AU_CURR', 'national_board', 'Foundation–Year 12. HSC/VCE/QCE.',    true, 1),
  ((SELECT id FROM countries WHERE iso_code='NZ'), 'New Zealand Curriculum',       'NCEA',    'national_board', 'Years 1-13. NCEA Levels 1-3.',        true, 1),
  ((SELECT id FROM countries WHERE iso_code='CA'), 'Canadian Provincial Curricula', 'CA_PROV', 'national_board', 'Ontario OSSD, BC Dogwood, etc.',      true, 1);


-- ============================================================
-- 4. EDUCATION LEVELS
-- ============================================================

-- Helper: ALL Indian school boards share the same 4-level structure.
-- We use a DO block to insert levels for every Indian board in one shot.
DO $$
DECLARE
  board_short TEXT;
  board_id UUID;
  indian_boards TEXT[] := ARRAY[
    'CBSE','ICSE','NIOS',
    'BSEAP','SEBA','BSEB','CGBSE','GBSHSE','GSHSEB','BSEH','HPBOSE',
    'JKBOSE','JAC','KSEEB','KBPE','MPBSE','MSBSHSE','BOSEM','MBOSE',
    'MBSE','NBSE','BSE_ODISHA','PSEB','RBSE','SBSE','TNSBSE','BSET',
    'TBSE','UPMSP','UBSE','WBBSE'
  ];
BEGIN
  FOREACH board_short IN ARRAY indian_boards LOOP
    SELECT id INTO board_id FROM education_systems WHERE short_name = board_short;
    IF board_id IS NULL THEN CONTINUE; END IF;

    -- Check if levels already exist for this board
    IF EXISTS (SELECT 1 FROM education_levels WHERE education_system_id = board_id) THEN
      CONTINUE;
    END IF;

    INSERT INTO education_levels (education_system_id, name, level_type, age_range, duration_years, sort_order) VALUES
      (board_id, 'Primary',          'primary',          '6-10',  5, 1),
      (board_id, 'Middle',           'middle',           '11-13', 3, 2),
      (board_id, 'Secondary',        'secondary',        '14-15', 2, 3),
      (board_id, 'Senior Secondary', 'senior_secondary', '16-17', 2, 4);
  END LOOP;
END $$;

-- US K-12
INSERT INTO education_levels (education_system_id, name, level_type, age_range, duration_years, sort_order) VALUES
  ((SELECT id FROM education_systems WHERE short_name='US_K12'), 'Elementary School', 'primary',   '5-10',  6, 1),
  ((SELECT id FROM education_systems WHERE short_name='US_K12'), 'Middle School',     'middle',    '11-13', 3, 2),
  ((SELECT id FROM education_systems WHERE short_name='US_K12'), 'High School',       'secondary', '14-18', 4, 3);

-- AP (sits inside High School)
INSERT INTO education_levels (education_system_id, name, level_type, age_range, duration_years, sort_order) VALUES
  ((SELECT id FROM education_systems WHERE short_name='AP'), 'AP Courses', 'secondary', '15-18', 2, 1);

-- UK
INSERT INTO education_levels (education_system_id, name, level_type, age_range, duration_years, sort_order) VALUES
  ((SELECT id FROM education_systems WHERE short_name='UK_NC'), 'Key Stage 1',           'primary',          '5-7',   2, 1),
  ((SELECT id FROM education_systems WHERE short_name='UK_NC'), 'Key Stage 2',           'primary',          '7-11',  4, 2),
  ((SELECT id FROM education_systems WHERE short_name='UK_NC'), 'Key Stage 3',           'middle',           '11-14', 3, 3),
  ((SELECT id FROM education_systems WHERE short_name='UK_NC'), 'Key Stage 4 (GCSE)',    'secondary',        '14-16', 2, 4),
  ((SELECT id FROM education_systems WHERE short_name='UK_NC'), 'Key Stage 5 (A-Level)', 'senior_secondary', '16-18', 2, 5);

-- SQA (Scotland)
INSERT INTO education_levels (education_system_id, name, level_type, age_range, duration_years, sort_order) VALUES
  ((SELECT id FROM education_systems WHERE short_name='SQA'), 'Nationals',        'secondary',        '14-16', 2, 1),
  ((SELECT id FROM education_systems WHERE short_name='SQA'), 'Highers',          'senior_secondary', '16-17', 1, 2),
  ((SELECT id FROM education_systems WHERE short_name='SQA'), 'Advanced Highers', 'senior_secondary', '17-18', 1, 3);

-- IB
INSERT INTO education_levels (education_system_id, name, level_type, age_range, duration_years, sort_order) VALUES
  ((SELECT id FROM education_systems WHERE short_name='IB'), 'Primary Years Programme (PYP)',  'primary',          '3-12',  9, 1),
  ((SELECT id FROM education_systems WHERE short_name='IB'), 'Middle Years Programme (MYP)',   'middle',           '11-16', 5, 2),
  ((SELECT id FROM education_systems WHERE short_name='IB'), 'Diploma Programme (DP)',         'senior_secondary', '16-19', 2, 3);

-- Cambridge
INSERT INTO education_levels (education_system_id, name, level_type, age_range, duration_years, sort_order) VALUES
  ((SELECT id FROM education_systems WHERE short_name='CAIE'), 'IGCSE',                  'secondary',        '14-16', 2, 1),
  ((SELECT id FROM education_systems WHERE short_name='CAIE'), 'Cambridge AS & A Level', 'senior_secondary', '16-19', 2, 2);

-- Australia
INSERT INTO education_levels (education_system_id, name, level_type, age_range, duration_years, sort_order) VALUES
  ((SELECT id FROM education_systems WHERE short_name='AU_CURR'), 'Primary',          'primary',          '5-12',  7, 1),
  ((SELECT id FROM education_systems WHERE short_name='AU_CURR'), 'Secondary',        'secondary',        '12-16', 4, 2),
  ((SELECT id FROM education_systems WHERE short_name='AU_CURR'), 'Senior Secondary', 'senior_secondary', '16-18', 2, 3);

-- New Zealand
INSERT INTO education_levels (education_system_id, name, level_type, age_range, duration_years, sort_order) VALUES
  ((SELECT id FROM education_systems WHERE short_name='NCEA'), 'Primary & Intermediate', 'primary',          '5-13',  8, 1),
  ((SELECT id FROM education_systems WHERE short_name='NCEA'), 'Secondary',              'secondary',        '13-18', 5, 2);

-- Canada
INSERT INTO education_levels (education_system_id, name, level_type, age_range, duration_years, sort_order) VALUES
  ((SELECT id FROM education_systems WHERE short_name='CA_PROV'), 'Elementary', 'primary',   '5-12', 7, 1),
  ((SELECT id FROM education_systems WHERE short_name='CA_PROV'), 'Secondary',  'secondary', '12-18', 6, 2);

-- India — Higher Education
INSERT INTO education_levels (education_system_id, name, level_type, age_range, duration_years, sort_order) VALUES
  ((SELECT id FROM education_systems WHERE short_name='IN_UNIV'), 'Diploma',       'diploma',       '16-19', 3, 1),
  ((SELECT id FROM education_systems WHERE short_name='IN_UNIV'), 'Undergraduate', 'undergraduate', '18-22', 4, 2),
  ((SELECT id FROM education_systems WHERE short_name='IN_UNIV'), 'Postgraduate',  'postgraduate',  '22-24', 2, 3),
  ((SELECT id FROM education_systems WHERE short_name='IN_UNIV'), 'Doctoral',      'doctoral',      '24-28', 4, 4);

-- India — Competitive Exams (each gets one level)
INSERT INTO education_levels (education_system_id, name, level_type, sort_order) VALUES
  ((SELECT id FROM education_systems WHERE short_name='JEE'),     'JEE Main + Advanced',  'competitive_exam', 1),
  ((SELECT id FROM education_systems WHERE short_name='NEET'),    'NEET UG',              'competitive_exam', 1),
  ((SELECT id FROM education_systems WHERE short_name='UPSC'),    'Civil Services Exam',  'competitive_exam', 1),
  ((SELECT id FROM education_systems WHERE short_name='CAT'),     'CAT Exam',             'competitive_exam', 1),
  ((SELECT id FROM education_systems WHERE short_name='GATE'),    'GATE Exam',            'competitive_exam', 1),
  ((SELECT id FROM education_systems WHERE short_name='CLAT'),    'CLAT Exam',            'competitive_exam', 1),
  ((SELECT id FROM education_systems WHERE short_name='NDA'),     'NDA Exam',             'competitive_exam', 1),
  ((SELECT id FROM education_systems WHERE short_name='SSC_CGL'), 'SSC CGL Exam',         'competitive_exam', 1),
  ((SELECT id FROM education_systems WHERE short_name='IBPS'),    'Banking Exam',         'competitive_exam', 1),
  ((SELECT id FROM education_systems WHERE short_name='CUET'),    'CUET Exam',            'competitive_exam', 1);


-- ============================================================
-- 5. GRADES
-- ============================================================

-- ALL Indian school boards: Classes 1-12 (using DO block for bulk)
DO $$
DECLARE
  board_short TEXT;
  board_id UUID;
  lvl_primary UUID; lvl_middle UUID; lvl_secondary UUID; lvl_senior UUID;
  indian_boards TEXT[] := ARRAY[
    'CBSE','ICSE','NIOS',
    'BSEAP','SEBA','BSEB','CGBSE','GBSHSE','GSHSEB','BSEH','HPBOSE',
    'JKBOSE','JAC','KSEEB','KBPE','MPBSE','MSBSHSE','BOSEM','MBOSE',
    'MBSE','NBSE','BSE_ODISHA','PSEB','RBSE','SBSE','TNSBSE','BSET',
    'TBSE','UPMSP','UBSE','WBBSE'
  ];
BEGIN
  FOREACH board_short IN ARRAY indian_boards LOOP
    SELECT id INTO board_id FROM education_systems WHERE short_name = board_short;
    IF board_id IS NULL THEN CONTINUE; END IF;

    SELECT id INTO lvl_primary   FROM education_levels WHERE education_system_id = board_id AND level_type = 'primary';
    SELECT id INTO lvl_middle    FROM education_levels WHERE education_system_id = board_id AND level_type = 'middle';
    SELECT id INTO lvl_secondary FROM education_levels WHERE education_system_id = board_id AND level_type = 'secondary';
    SELECT id INTO lvl_senior    FROM education_levels WHERE education_system_id = board_id AND level_type = 'senior_secondary';

    -- Skip if grades already exist
    IF EXISTS (SELECT 1 FROM grades WHERE education_level_id = lvl_primary) THEN CONTINUE; END IF;

    -- NIOS only has secondary + senior secondary
    IF board_short = 'NIOS' THEN
      IF lvl_secondary IS NOT NULL THEN
        INSERT INTO grades (education_level_id, name, display_name, numeric_value, sort_order) VALUES
          (lvl_secondary, 'Class 10', '10th Standard', 10, 10);
      END IF;
      IF lvl_senior IS NOT NULL THEN
        INSERT INTO grades (education_level_id, name, display_name, numeric_value, sort_order) VALUES
          (lvl_senior, 'Class 12', '12th Standard', 12, 12);
      END IF;
      CONTINUE;
    END IF;

    -- Regular boards: Classes 1-12
    IF lvl_primary IS NOT NULL THEN
      INSERT INTO grades (education_level_id, name, display_name, numeric_value, sort_order) VALUES
        (lvl_primary, 'Class 1', '1st Standard', 1, 1),
        (lvl_primary, 'Class 2', '2nd Standard', 2, 2),
        (lvl_primary, 'Class 3', '3rd Standard', 3, 3),
        (lvl_primary, 'Class 4', '4th Standard', 4, 4),
        (lvl_primary, 'Class 5', '5th Standard', 5, 5);
    END IF;
    IF lvl_middle IS NOT NULL THEN
      INSERT INTO grades (education_level_id, name, display_name, numeric_value, sort_order) VALUES
        (lvl_middle, 'Class 6', '6th Standard', 6, 6),
        (lvl_middle, 'Class 7', '7th Standard', 7, 7),
        (lvl_middle, 'Class 8', '8th Standard', 8, 8);
    END IF;
    IF lvl_secondary IS NOT NULL THEN
      INSERT INTO grades (education_level_id, name, display_name, numeric_value, sort_order) VALUES
        (lvl_secondary, 'Class 9',  '9th Standard',  9,  9),
        (lvl_secondary, 'Class 10', '10th Standard', 10, 10);
    END IF;
    IF lvl_senior IS NOT NULL THEN
      INSERT INTO grades (education_level_id, name, display_name, numeric_value, sort_order) VALUES
        (lvl_senior, 'Class 11', '11th Standard', 11, 11),
        (lvl_senior, 'Class 12', '12th Standard', 12, 12);
    END IF;
  END LOOP;
END $$;

-- US K-12
INSERT INTO grades (education_level_id, name, display_name, numeric_value, sort_order)
SELECT el.id, g.name, g.display_name, g.numeric_value, g.sort_order
FROM (VALUES
  ('Elementary School', 'Kindergarten', 'K',         0,  0),
  ('Elementary School', 'Grade 1',     '1st Grade',  1,  1),
  ('Elementary School', 'Grade 2',     '2nd Grade',  2,  2),
  ('Elementary School', 'Grade 3',     '3rd Grade',  3,  3),
  ('Elementary School', 'Grade 4',     '4th Grade',  4,  4),
  ('Elementary School', 'Grade 5',     '5th Grade',  5,  5),
  ('Middle School',     'Grade 6',     '6th Grade',  6,  6),
  ('Middle School',     'Grade 7',     '7th Grade',  7,  7),
  ('Middle School',     'Grade 8',     '8th Grade',  8,  8),
  ('High School',       'Grade 9',     'Freshman',   9,  9),
  ('High School',       'Grade 10',    'Sophomore',  10, 10),
  ('High School',       'Grade 11',    'Junior',     11, 11),
  ('High School',       'Grade 12',    'Senior',     12, 12)
) AS g(level_name, name, display_name, numeric_value, sort_order)
JOIN education_levels el ON el.name = g.level_name
  AND el.education_system_id = (SELECT id FROM education_systems WHERE short_name = 'US_K12');

-- AP: Grades 9-12 mirror
INSERT INTO grades (education_level_id, name, display_name, numeric_value, sort_order) VALUES
  ((SELECT id FROM education_levels WHERE education_system_id = (SELECT id FROM education_systems WHERE short_name='AP')),
   'AP Year 1', 'Junior AP', 11, 1),
  ((SELECT id FROM education_levels WHERE education_system_id = (SELECT id FROM education_systems WHERE short_name='AP')),
   'AP Year 2', 'Senior AP', 12, 2);

-- UK Years 1-13
INSERT INTO grades (education_level_id, name, display_name, numeric_value, sort_order)
SELECT el.id, g.name, g.display_name, g.numeric_value, g.sort_order
FROM (VALUES
  ('Key Stage 1',           'Year 1',  'Year 1',   1,  1),
  ('Key Stage 1',           'Year 2',  'Year 2',   2,  2),
  ('Key Stage 2',           'Year 3',  'Year 3',   3,  3),
  ('Key Stage 2',           'Year 4',  'Year 4',   4,  4),
  ('Key Stage 2',           'Year 5',  'Year 5',   5,  5),
  ('Key Stage 2',           'Year 6',  'Year 6',   6,  6),
  ('Key Stage 3',           'Year 7',  'Year 7',   7,  7),
  ('Key Stage 3',           'Year 8',  'Year 8',   8,  8),
  ('Key Stage 3',           'Year 9',  'Year 9',   9,  9),
  ('Key Stage 4 (GCSE)',    'Year 10', 'Year 10',  10, 10),
  ('Key Stage 4 (GCSE)',    'Year 11', 'Year 11',  11, 11),
  ('Key Stage 5 (A-Level)', 'Year 12', 'Year 12',  12, 12),
  ('Key Stage 5 (A-Level)', 'Year 13', 'Year 13',  13, 13)
) AS g(level_name, name, display_name, numeric_value, sort_order)
JOIN education_levels el ON el.name = g.level_name
  AND el.education_system_id = (SELECT id FROM education_systems WHERE short_name = 'UK_NC');

-- SQA (Scotland)
INSERT INTO grades (education_level_id, name, display_name, numeric_value, sort_order) VALUES
  ((SELECT id FROM education_levels WHERE education_system_id=(SELECT id FROM education_systems WHERE short_name='SQA') AND name='Nationals'),
   'S4', 'S4 (National 5)', 4, 1),
  ((SELECT id FROM education_levels WHERE education_system_id=(SELECT id FROM education_systems WHERE short_name='SQA') AND name='Nationals'),
   'S5', 'S5', 5, 2),
  ((SELECT id FROM education_levels WHERE education_system_id=(SELECT id FROM education_systems WHERE short_name='SQA') AND name='Highers'),
   'S5 Higher', 'Higher Year', 5, 1),
  ((SELECT id FROM education_levels WHERE education_system_id=(SELECT id FROM education_systems WHERE short_name='SQA') AND name='Advanced Highers'),
   'S6 Advanced', 'Advanced Higher Year', 6, 1);

-- IB grades
INSERT INTO grades (education_level_id, name, display_name, numeric_value, sort_order)
SELECT el.id, g.name, g.display_name, g.numeric_value, g.sort_order
FROM (VALUES
  ('Primary Years Programme (PYP)',  'PYP Year 1', 'PYP 1', 1, 1),
  ('Primary Years Programme (PYP)',  'PYP Year 2', 'PYP 2', 2, 2),
  ('Primary Years Programme (PYP)',  'PYP Year 3', 'PYP 3', 3, 3),
  ('Primary Years Programme (PYP)',  'PYP Year 4', 'PYP 4', 4, 4),
  ('Primary Years Programme (PYP)',  'PYP Year 5', 'PYP 5', 5, 5),
  ('Primary Years Programme (PYP)',  'PYP Year 6', 'PYP 6', 6, 6),
  ('Middle Years Programme (MYP)',   'MYP Year 1', 'MYP 1', 1, 1),
  ('Middle Years Programme (MYP)',   'MYP Year 2', 'MYP 2', 2, 2),
  ('Middle Years Programme (MYP)',   'MYP Year 3', 'MYP 3', 3, 3),
  ('Middle Years Programme (MYP)',   'MYP Year 4', 'MYP 4', 4, 4),
  ('Middle Years Programme (MYP)',   'MYP Year 5', 'MYP 5', 5, 5),
  ('Diploma Programme (DP)',         'DP Year 1',  'IB DP 1', 1, 1),
  ('Diploma Programme (DP)',         'DP Year 2',  'IB DP 2', 2, 2)
) AS g(level_name, name, display_name, numeric_value, sort_order)
JOIN education_levels el ON el.name = g.level_name
  AND el.education_system_id = (SELECT id FROM education_systems WHERE short_name = 'IB');

-- Cambridge
INSERT INTO grades (education_level_id, name, display_name, numeric_value, sort_order) VALUES
  ((SELECT id FROM education_levels WHERE education_system_id=(SELECT id FROM education_systems WHERE short_name='CAIE') AND name='IGCSE'),
   'IGCSE Year 1', 'IGCSE 1', 1, 1),
  ((SELECT id FROM education_levels WHERE education_system_id=(SELECT id FROM education_systems WHERE short_name='CAIE') AND name='IGCSE'),
   'IGCSE Year 2', 'IGCSE 2', 2, 2),
  ((SELECT id FROM education_levels WHERE education_system_id=(SELECT id FROM education_systems WHERE short_name='CAIE') AND name='Cambridge AS & A Level'),
   'AS Level', 'AS', 1, 1),
  ((SELECT id FROM education_levels WHERE education_system_id=(SELECT id FROM education_systems WHERE short_name='CAIE') AND name='Cambridge AS & A Level'),
   'A Level',  'A2', 2, 2);

-- Australia
INSERT INTO grades (education_level_id, name, display_name, numeric_value, sort_order)
SELECT el.id, g.name, g.display_name, g.numeric_value, g.sort_order
FROM (VALUES
  ('Primary',          'Foundation', 'Prep',     0, 0),
  ('Primary',          'Year 1',    'Year 1',   1, 1),
  ('Primary',          'Year 2',    'Year 2',   2, 2),
  ('Primary',          'Year 3',    'Year 3',   3, 3),
  ('Primary',          'Year 4',    'Year 4',   4, 4),
  ('Primary',          'Year 5',    'Year 5',   5, 5),
  ('Primary',          'Year 6',    'Year 6',   6, 6),
  ('Secondary',        'Year 7',    'Year 7',   7, 7),
  ('Secondary',        'Year 8',    'Year 8',   8, 8),
  ('Secondary',        'Year 9',    'Year 9',   9, 9),
  ('Secondary',        'Year 10',   'Year 10', 10, 10),
  ('Senior Secondary', 'Year 11',   'Year 11', 11, 11),
  ('Senior Secondary', 'Year 12',   'Year 12', 12, 12)
) AS g(level_name, name, display_name, numeric_value, sort_order)
JOIN education_levels el ON el.name = g.level_name
  AND el.education_system_id = (SELECT id FROM education_systems WHERE short_name = 'AU_CURR');

-- New Zealand
INSERT INTO grades (education_level_id, name, display_name, numeric_value, sort_order)
SELECT el.id, g.name, g.display_name, g.numeric_value, g.sort_order
FROM (VALUES
  ('Primary & Intermediate', 'Year 1',  'Year 1',  1, 1),
  ('Primary & Intermediate', 'Year 2',  'Year 2',  2, 2),
  ('Primary & Intermediate', 'Year 3',  'Year 3',  3, 3),
  ('Primary & Intermediate', 'Year 4',  'Year 4',  4, 4),
  ('Primary & Intermediate', 'Year 5',  'Year 5',  5, 5),
  ('Primary & Intermediate', 'Year 6',  'Year 6',  6, 6),
  ('Primary & Intermediate', 'Year 7',  'Year 7',  7, 7),
  ('Primary & Intermediate', 'Year 8',  'Year 8',  8, 8),
  ('Secondary',              'Year 9',  'Year 9',  9, 9),
  ('Secondary',              'Year 10', 'Year 10', 10, 10),
  ('Secondary',              'Year 11', 'NCEA L1', 11, 11),
  ('Secondary',              'Year 12', 'NCEA L2', 12, 12),
  ('Secondary',              'Year 13', 'NCEA L3', 13, 13)
) AS g(level_name, name, display_name, numeric_value, sort_order)
JOIN education_levels el ON el.name = g.level_name
  AND el.education_system_id = (SELECT id FROM education_systems WHERE short_name = 'NCEA');

-- Canada
INSERT INTO grades (education_level_id, name, display_name, numeric_value, sort_order)
SELECT el.id, g.name, g.display_name, g.numeric_value, g.sort_order
FROM (VALUES
  ('Elementary', 'Kindergarten', 'K',           0, 0),
  ('Elementary', 'Grade 1',     'Grade 1',      1, 1),
  ('Elementary', 'Grade 2',     'Grade 2',      2, 2),
  ('Elementary', 'Grade 3',     'Grade 3',      3, 3),
  ('Elementary', 'Grade 4',     'Grade 4',      4, 4),
  ('Elementary', 'Grade 5',     'Grade 5',      5, 5),
  ('Elementary', 'Grade 6',     'Grade 6',      6, 6),
  ('Secondary',  'Grade 7',     'Grade 7',      7, 7),
  ('Secondary',  'Grade 8',     'Grade 8',      8, 8),
  ('Secondary',  'Grade 9',     'Grade 9',      9, 9),
  ('Secondary',  'Grade 10',    'Grade 10',    10, 10),
  ('Secondary',  'Grade 11',    'Grade 11',    11, 11),
  ('Secondary',  'Grade 12',    'Grade 12',    12, 12)
) AS g(level_name, name, display_name, numeric_value, sort_order)
JOIN education_levels el ON el.name = g.level_name
  AND el.education_system_id = (SELECT id FROM education_systems WHERE short_name = 'CA_PROV');

-- Competitive exams: single "Preparation" grade each
DO $$
DECLARE
  exam_short TEXT;
  lvl_id UUID;
  exam_shorts TEXT[] := ARRAY['JEE','NEET','UPSC','CAT','GATE','CLAT','NDA','SSC_CGL','IBPS','CUET'];
BEGIN
  FOREACH exam_short IN ARRAY exam_shorts LOOP
    SELECT el.id INTO lvl_id FROM education_levels el
    JOIN education_systems es ON el.education_system_id = es.id
    WHERE es.short_name = exam_short LIMIT 1;
    IF lvl_id IS NULL THEN CONTINUE; END IF;
    IF EXISTS (SELECT 1 FROM grades WHERE education_level_id = lvl_id) THEN CONTINUE; END IF;
    INSERT INTO grades (education_level_id, name, display_name, numeric_value, sort_order) VALUES
      (lvl_id, 'Preparation', exam_short || ' Prep', 1, 1);
  END LOOP;
END $$;

-- Higher education: degree programs as grades
DO $$
DECLARE univ_id UUID; lvl_ug UUID; lvl_pg UUID; lvl_dip UUID;
BEGIN
  SELECT id INTO univ_id FROM education_systems WHERE short_name = 'IN_UNIV';
  SELECT id INTO lvl_dip FROM education_levels WHERE education_system_id = univ_id AND level_type = 'diploma';
  SELECT id INTO lvl_ug  FROM education_levels WHERE education_system_id = univ_id AND level_type = 'undergraduate';
  SELECT id INTO lvl_pg  FROM education_levels WHERE education_system_id = univ_id AND level_type = 'postgraduate';

  IF NOT EXISTS (SELECT 1 FROM grades WHERE education_level_id = lvl_ug) THEN
    INSERT INTO grades (education_level_id, name, display_name, numeric_value, sort_order) VALUES
      (lvl_dip, 'Diploma',    'Polytechnic/ITI', 1, 1),
      (lvl_ug,  'B.Tech',     'B.Tech/B.E.',     1, 1),
      (lvl_ug,  'B.Sc',       'B.Sc.',           2, 2),
      (lvl_ug,  'B.Com',      'B.Com.',           3, 3),
      (lvl_ug,  'B.A.',       'B.A.',             4, 4),
      (lvl_ug,  'MBBS',       'MBBS',             5, 5),
      (lvl_ug,  'BBA',        'BBA/BMS',          6, 6),
      (lvl_ug,  'LLB',        'LL.B.',            7, 7),
      (lvl_ug,  'B.Arch',     'B.Arch.',          8, 8),
      (lvl_ug,  'B.Pharm',    'B.Pharm.',         9, 9),
      (lvl_ug,  'B.Ed',       'B.Ed.',           10,10),
      (lvl_pg,  'M.Tech',     'M.Tech/M.E.',     1, 1),
      (lvl_pg,  'M.Sc',       'M.Sc.',            2, 2),
      (lvl_pg,  'MBA',        'MBA',              3, 3),
      (lvl_pg,  'M.A.',       'M.A.',             4, 4),
      (lvl_pg,  'MCA',        'MCA',              5, 5);
  END IF;
END $$;


-- ============================================================
-- 6. STREAMS
-- ============================================================

-- ALL Indian boards: General stream for Classes 1-10, specialized for 11-12
DO $$
DECLARE
  board_short TEXT;
  board_id UUID;
  grade_rec RECORD;
  indian_boards TEXT[] := ARRAY[
    'CBSE','ICSE','NIOS',
    'BSEAP','SEBA','BSEB','CGBSE','GBSHSE','GSHSEB','BSEH','HPBOSE',
    'JKBOSE','JAC','KSEEB','KBPE','MPBSE','MSBSHSE','BOSEM','MBOSE',
    'MBSE','NBSE','BSE_ODISHA','PSEB','RBSE','SBSE','TNSBSE','BSET',
    'TBSE','UPMSP','UBSE','WBBSE'
  ];
BEGIN
  FOREACH board_short IN ARRAY indian_boards LOOP
    SELECT id INTO board_id FROM education_systems WHERE short_name = board_short;
    IF board_id IS NULL THEN CONTINUE; END IF;

    FOR grade_rec IN
      SELECT g.id AS grade_id, g.numeric_value
      FROM grades g
      JOIN education_levels el ON g.education_level_id = el.id
      WHERE el.education_system_id = board_id
    LOOP
      -- Skip if streams already exist for this grade
      IF EXISTS (SELECT 1 FROM streams WHERE grade_id = grade_rec.grade_id) THEN CONTINUE; END IF;

      IF grade_rec.numeric_value <= 10 OR grade_rec.numeric_value IS NULL THEN
        -- Classes 1-10 / NIOS / competitive: General only
        INSERT INTO streams (grade_id, name, is_default, sort_order)
        VALUES (grade_rec.grade_id, 'General', true, 0);
      ELSE
        -- Classes 11-12: Science (PCM), Science (PCB), Commerce, Arts + General default
        INSERT INTO streams (grade_id, name, description, is_default, sort_order) VALUES
          (grade_rec.grade_id, 'Science (PCM)', 'Physics, Chemistry, Mathematics',          false, 1),
          (grade_rec.grade_id, 'Science (PCB)', 'Physics, Chemistry, Biology',              false, 2),
          (grade_rec.grade_id, 'Commerce',      'Accountancy, Business Studies, Economics', false, 3),
          (grade_rec.grade_id, 'Arts',          'History, Political Science, Geography',    false, 4),
          (grade_rec.grade_id, 'General',       'Default stream',                           true,  5);
      END IF;
    END LOOP;
  END LOOP;
END $$;

-- US, UK, IB, Cambridge, Australia, NZ, Canada, AP, SQA: General stream for all grades
DO $$
DECLARE
  sys_short TEXT;
  grade_rec RECORD;
  intl_systems TEXT[] := ARRAY['US_K12','AP','UK_NC','SQA','IB','CAIE','AU_CURR','NCEA','CA_PROV'];
BEGIN
  FOREACH sys_short IN ARRAY intl_systems LOOP
    FOR grade_rec IN
      SELECT g.id AS grade_id
      FROM grades g
      JOIN education_levels el ON g.education_level_id = el.id
      JOIN education_systems es ON el.education_system_id = es.id
      WHERE es.short_name = sys_short
    LOOP
      IF NOT EXISTS (SELECT 1 FROM streams WHERE grade_id = grade_rec.grade_id) THEN
        INSERT INTO streams (grade_id, name, is_default, sort_order)
        VALUES (grade_rec.grade_id, 'General', true, 0);
      END IF;
    END LOOP;
  END LOOP;
END $$;

-- Competitive exams & higher education: General stream for all grades
DO $$
DECLARE grade_rec RECORD;
BEGIN
  FOR grade_rec IN
    SELECT g.id AS grade_id
    FROM grades g
    JOIN education_levels el ON g.education_level_id = el.id
    JOIN education_systems es ON el.education_system_id = es.id
    WHERE es.system_type IN ('competitive_exam', 'university')
  LOOP
    IF NOT EXISTS (SELECT 1 FROM streams WHERE grade_id = grade_rec.grade_id) THEN
      INSERT INTO streams (grade_id, name, is_default, sort_order)
      VALUES (grade_rec.grade_id, 'General', true, 0);
    END IF;
  END LOOP;
END $$;

-- ============================================================
-- SEED COMPLETE. Summary:
--   7 regions, 37 countries
--   ~55 education systems (3 national + 28 state + 10 competitive + 1 university + intl + US/UK/AU/NZ/CA)
--   ~170 education levels (31 Indian boards × 4 + US/UK/IB/CAIE/AU/NZ/CA/AP/SQA + competitive + university)
--   ~500+ grades (31 boards × 12 + US 13 + UK 13 + IB 13 + CAIE 4 + AU 13 + NZ 13 + CA 13 + competitive + university)
--   ~700+ streams (every grade has at least 1; Indian 11-12 have 5 each)
-- ============================================================
