"""Test-environment helper: reset local Supabase, run migrations, seed, and
optionally run the integration tests.

Usage:

    python backend/scripts/test_env.py            # reset + migrate + seed
    python backend/scripts/test_env.py --tests    # also run pytest

Requirements: supabase CLI must be installed and ``supabase start`` running.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MIGRATIONS = REPO / "supabase" / "migrations"
SEED = REPO / "supabase" / "seed.sql"


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=REPO, **kwargs)


def main():
    print("=" * 60)
    print("Vinci Automation — Test Environment Setup")
    print("=" * 60)

    # ---- 1. Reset local database (drops everything, re-applies migrations) --
    print("\n[1/4] Resetting local Supabase database …")
    result = run(["supabase", "db", "reset", "--linked"])
    if result.returncode != 0:
        print("ERROR: supabase db reset failed.", file=sys.stderr)
        sys.exit(1)
    print("  ✓ Database reset complete.")

    # ---- 2. Apply all migrations in order (redundant after reset, but safe) --
    print("\n[2/4] Applying all migrations …")
    for m in sorted(MIGRATIONS.glob("*.sql")):
        if m.name.startswith("0002"):
            continue  # skip seed migration — handled below
        print(f"  Applying {m.name} …")
        result = run(["supabase", "db", "execute", "--file", str(m)])
        if result.returncode != 0:
            print(f"ERROR: migration {m.name} failed.", file=sys.stderr)
            sys.exit(1)
    print("  ✓ All migrations applied.")

    # ---- 3. Seed with base data (0002 includes schools/courses/teachers) ----
    print("\n[3/4] Seeding base data …")
    seed_file = MIGRATIONS / "0002_seed_airtable.sql"
    if seed_file.exists():
        result = run(["supabase", "db", "execute", "--file", str(seed_file)])
        if result.returncode != 0:
            print("WARN: seed file may have already been applied (reset already does this).")
        else:
            print("  ✓ Seed data loaded.")
    else:
        print("  SKIP: no seed file found.")

    # ---- 4. Verify lesson_income column exists ----
    print("\n[4/4] Verifying schema …")
    result = run(
        ["supabase", "db", "execute"],
        input='SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name=\'lessons\' AND column_name=\'lesson_income\';',
        text=True,
        capture_output=True,
    )
    if "lesson_income" in result.stdout:
        print("  ✓ lesson_income column exists.\n")
    else:
        print("  ✗ lesson_income column NOT found. Did migration 0004 run?\n")
        sys.exit(1)

    # ---- 5. Optionally run integration tests ----
    if "--tests" in sys.argv:
        print("Running integration tests …")
        os.chdir(REPO)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "backend/tests/", "-v"],
            cwd=REPO,
        )
        if result.returncode != 0:
            print("Some tests failed.", file=sys.stderr)
            sys.exit(1)
        print("  ✓ All tests passed.")

    print("Done. Backend + frontend can now be started locally:")
    print("  backend :  cd backend && uvicorn app.main:app --reload")
    print("  frontend:  cd frontend && npm run dev")


if __name__ == "__main__":
    main()
