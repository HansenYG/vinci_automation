"""One-time Airtable -> Supabase migration. Run from the backend/ directory:

    python -m scripts.migrate_airtable

Needs AIRTABLE_API_KEY + AIRTABLE_BASE_ID + SUPABASE_* in .env.
"""

from app.core.database import get_supabase
from app.services import airtable


def main() -> None:
    db = get_supabase()
    result = airtable.run_migration(db)
    print(f"Migrated: {result['teachers']} teacher(s), {result['lessons']} lesson(s).")


if __name__ == "__main__":
    main()
