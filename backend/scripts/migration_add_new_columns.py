"""
migration_add_new_columns.py
============================
Adds the new columns introduced in this patch to existing tables.
Safe to run on an existing database — skips columns that already exist.

Run once:
    cd backend
    python scripts/migration_add_new_columns.py

Adds:
  sl_citations         → year, volume, reporter, page
  legal_documents      → executive_summary, detailed_summary
  legal_entities       → (new table created if missing)
"""

import sys
from pathlib import Path

# Ensure backend root is on path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import engine
from sqlalchemy import text, inspect


def column_exists(inspector, table_name: str, column_name: str) -> bool:
    cols = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in cols


def table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def run():
    inspector = inspect(engine)

    with engine.begin() as conn:

        # ── sl_citations: add year, volume, reporter, page ────────────────────
        if table_exists(inspector, "sl_citations"):
            for col, col_type in [
                ("year",     "INTEGER"),
                ("volume",   "INTEGER"),
                ("reporter", "VARCHAR(10)"),
                ("page",     "INTEGER"),
            ]:
                if not column_exists(inspector, "sl_citations", col):
                    conn.execute(text(
                        f"ALTER TABLE sl_citations ADD COLUMN {col} {col_type}"
                    ))
                    print(f"  ✅ Added sl_citations.{col}")
                else:
                    print(f"  ⏭  sl_citations.{col} already exists")
        else:
            print("  ⚠️  sl_citations table not found — skipping")

        # ── legal_documents: add executive_summary, detailed_summary ──────────
        if table_exists(inspector, "legal_documents"):
            for col in ["executive_summary", "detailed_summary"]:
                if not column_exists(inspector, "legal_documents", col):
                    conn.execute(text(
                        f"ALTER TABLE legal_documents ADD COLUMN {col} TEXT"
                    ))
                    print(f"  ✅ Added legal_documents.{col}")
                else:
                    print(f"  ⏭  legal_documents.{col} already exists")
        else:
            print("  ⚠️  legal_documents table not found — skipping")

        # ── legal_entities: create table if missing ────────────────────────────
        if not table_exists(inspector, "legal_entities"):
            conn.execute(text("""
                CREATE TABLE legal_entities (
                    id          SERIAL PRIMARY KEY,
                    document_id INTEGER NOT NULL
                                REFERENCES legal_documents(id) ON DELETE CASCADE,
                    entity_text VARCHAR(500) NOT NULL,
                    entity_type VARCHAR(50)  NOT NULL,
                    char_start  INTEGER,
                    char_end    INTEGER
                )
            """))
            conn.execute(text(
                "CREATE INDEX ix_legal_entities_document_id "
                "ON legal_entities(document_id)"
            ))
            print("  ✅ Created legal_entities table")
        else:
            print("  ⏭  legal_entities table already exists")

    print("\n✅ Migration complete.")


if __name__ == "__main__":
    run()