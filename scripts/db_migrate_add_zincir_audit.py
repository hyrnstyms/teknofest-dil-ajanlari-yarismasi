"""Manually add Case chain and field-level audit columns."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)


def migrate(database_url: str) -> list[str]:
    engine = create_engine(database_url, pool_pre_ping=True)
    applied: list[str] = []
    try:
        with engine.begin() as connection:
            inspector = inspect(connection)
            case_columns = {column["name"] for column in inspector.get_columns("cases")}
            event_columns = {column["name"] for column in inspector.get_columns("case_events")}
            json_type = "JSONB" if connection.dialect.name == "postgresql" else "JSON"
            statements: list[tuple[str, str]] = []
            if "zincir_id" not in case_columns:
                statements.append(("cases.zincir_id", "ALTER TABLE cases ADD COLUMN zincir_id VARCHAR(36)"))
            if "before_value" not in event_columns:
                statements.append(("case_events.before_value", f"ALTER TABLE case_events ADD COLUMN before_value {json_type}"))
            if "after_value" not in event_columns:
                statements.append(("case_events.after_value", f"ALTER TABLE case_events ADD COLUMN after_value {json_type}"))
            for label, statement in statements:
                connection.execute(text(statement))
                applied.append(label)
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_cases_zincir_id ON cases (zincir_id)"))
    finally:
        engine.dispose()
    return applied


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", "").strip())
    args = parser.parse_args()
    if not args.database_url:
        parser.error("DATABASE_URL is required; use --database-url.")
    applied = migrate(args.database_url)
    print("Applied changes:", ", ".join(applied) if applied else "none (schema is current)")


if __name__ == "__main__":
    main()
