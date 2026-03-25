import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")

# Fallback models when daily quota (RPD) is exhausted on the primary model.
GEMINI_FALLBACK_MODELS = [
    GEMINI_MODEL,               # Try primary first (Pro plan: 1000 RPD)
    "gemini-2.5-flash",         # Fallback
    "gemini-2.5-flash-lite",    # Fallback
]
# Deduplicate while preserving order
GEMINI_FALLBACK_MODELS = list(dict.fromkeys(GEMINI_FALLBACK_MODELS))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not set in .env")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set in .env")
