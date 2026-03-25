"""
Seed runner — reads and executes SQL files against Supabase via the REST RPC endpoint.
Since supabase-py doesn't support raw SQL execution, we use the PostgREST pgnet
or just read and execute via the management API.

For Supabase, the easiest way is to run seed.sql directly in the Supabase SQL Editor.
This module provides a Python fallback that uses httpx to call the /rest/v1/rpc endpoint.
"""
import os
import logging
import httpx

from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)


def run_sql_via_supabase(sql: str) -> dict:
    """
    Execute raw SQL against Supabase using the pg_net / SQL execution endpoint.
    Supabase exposes a /rest/v1/rpc endpoint but raw SQL requires the management API
    or direct psql connection.

    For the seed, we split into individual statements and run them via the
    Supabase Management API's /sql endpoint.
    """
    # Supabase Management API for raw SQL
    # This uses the service_role key for auth
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    # Use the PostgREST /rpc/exec_sql if you've created that function,
    # or use Supabase's built-in SQL execution
    # The most reliable method is the Supabase Platform API:
    url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"

    try:
        response = httpx.post(
            url,
            json={"query": sql},
            headers=headers,
            timeout=120,
        )
        if response.status_code == 200:
            return {"ok": True, "data": response.json()}
        else:
            return {"ok": False, "error": response.text, "status": response.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def read_sql_file(filename: str) -> str:
    """Read a .sql file from the backend directory."""
    path = os.path.join(os.path.dirname(__file__), filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def run_seed():
    """Execute migration.sql then seed.sql."""
    results = []

    # Step 1: Migration (add missing columns)
    migration_sql = read_sql_file("migration.sql")
    logger.info("Running migration.sql...")
    res = run_sql_via_supabase(migration_sql)
    results.append({"file": "migration.sql", **res})

    # Step 2: Seed data
    seed_sql = read_sql_file("seed.sql")
    logger.info("Running seed.sql...")
    res = run_sql_via_supabase(seed_sql)
    results.append({"file": "seed.sql", **res})

    return results
