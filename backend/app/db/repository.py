"""Single persistence boundary for KAMUAI analyses and review events."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Select, delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.database import (
    DatabaseUnavailableError,
    assert_database_available,
    create_database_engine,
    create_session_factory,
)
from backend.app.db.models import Analysis, Base, ReviewEvent


def json_safe(value: Any) -> Any:
    """Convert supported runtime values into JSON-compatible values."""
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if isinstance(value, (datetime, date, Path)):
        return str(value)
    if hasattr(value, "model_dump"):
        return json_safe(value.model_dump())
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


class AnalysisRepository:
    def __init__(self, database_url: str | None = None, engine: Engine | None = None):
        self.engine = engine or create_database_engine(database_url)
        self.session_factory: sessionmaker = create_session_factory(self.engine)
        try:
            assert_database_available(self.engine)
            Base.metadata.create_all(self.engine)
        except DatabaseUnavailableError:
            raise
        except Exception as exc:
            raise DatabaseUnavailableError(
                f"PostgreSQL şeması hazırlanamadı: {exc}"
            ) from exc

    def health_check(self) -> None:
        assert_database_available(self.engine)

    @staticmethod
    def _columns(state: dict[str, Any]) -> dict[str, Any]:
        document = state.get("document") or {}
        routing = state.get("routing") or {}
        review = state.get("human_review") or {}
        return {
            "institution_id": state.get("institution_id") or state.get("kurum_profili_id"),
            "document_type": document.get("document_type"),
            "process_intent": document.get("process_intent"),
            "status": review.get("status"),
            "recommended_unit": routing.get("recommended_unit"),
        }

    @staticmethod
    def _state_from_row(row: Analysis) -> dict[str, Any]:
        state = dict(row.state_json or {})
        state.setdefault("analysis_id", row.analysis_id)
        if state.get("created_at") is None:
            state["created_at"] = row.created_at.isoformat() if row.created_at else None
        return state

    def save_analysis(self, analysis_id: str, state: dict[str, Any]) -> None:
        self._write_analysis(analysis_id, state)

    def update_analysis(self, analysis_id: str, state: dict[str, Any]) -> None:
        self._write_analysis(analysis_id, state, require_existing=True)

    def _write_analysis(
        self, analysis_id: str, state: dict[str, Any], require_existing: bool = False
    ) -> None:
        normalized = json_safe(state)
        normalized["analysis_id"] = analysis_id
        columns = self._columns(normalized)
        with self.session_factory.begin() as session:
            row = session.get(Analysis, analysis_id)
            if row is None:
                if require_existing:
                    raise KeyError(analysis_id)
                session.add(Analysis(analysis_id=analysis_id, state_json=normalized, **columns))
            else:
                row.state_json = normalized
                for name, value in columns.items():
                    setattr(row, name, value)

    def get_analysis(self, analysis_id: str) -> dict[str, Any] | None:
        with self.session_factory() as session:
            row = session.get(Analysis, analysis_id)
            return self._state_from_row(row) if row is not None else None

    def list_analyses(
        self,
        *,
        status: str | None = None,
        document_type: str | None = None,
        process_intent: str | None = None,
    ) -> list[dict[str, Any]]:
        statement: Select = select(Analysis).order_by(Analysis.created_at.desc())
        if status:
            statement = statement.where(Analysis.status == status)
        if document_type:
            statement = statement.where(Analysis.document_type == document_type)
        if process_intent:
            statement = statement.where(Analysis.process_intent == process_intent)
        with self.session_factory() as session:
            return [self._state_from_row(row) for row in session.scalars(statement)]

    def list_pending_reviews(self) -> list[dict[str, Any]]:
        statement = (
            select(Analysis)
            .where(Analysis.status == "pending_review")
            .order_by(Analysis.created_at.desc())
        )
        with self.session_factory() as session:
            states = [self._state_from_row(row) for row in session.scalars(statement)]
        return [
            state for state in states
            if (state.get("human_review") or {}).get("status") == "pending_review"
            and (
                (state.get("human_review") or {}).get("required") is True
                or state.get("requires_human_approval") is True
                or state.get("requires_human_review") is True
            )
        ]

    def record_review_event(self, analysis_id: str, action: str, payload: dict[str, Any]) -> None:
        with self.session_factory.begin() as session:
            if session.get(Analysis, analysis_id) is None:
                raise KeyError(analysis_id)
            session.add(ReviewEvent(analysis_id=analysis_id, action=action, payload=json_safe(payload)))

    def update_analysis_with_event(
        self, analysis_id: str, state: dict[str, Any], action: str, payload: dict[str, Any]
    ) -> None:
        normalized = json_safe(state)
        normalized["analysis_id"] = analysis_id
        columns = self._columns(normalized)
        with self.session_factory.begin() as session:
            row = session.get(Analysis, analysis_id)
            if row is None:
                raise KeyError(analysis_id)
            row.state_json = normalized
            for name, value in columns.items():
                setattr(row, name, value)
            session.add(ReviewEvent(analysis_id=analysis_id, action=action, payload=json_safe(payload)))

    def list_review_events(self, analysis_id: str) -> list[dict[str, Any]]:
        statement = select(ReviewEvent).where(ReviewEvent.analysis_id == analysis_id).order_by(ReviewEvent.id)
        with self.session_factory() as session:
            return [
                {"id": event.id, "analysis_id": event.analysis_id, "action": event.action,
                 "payload": dict(event.payload or {}),
                 "created_at": event.created_at.isoformat() if event.created_at else None}
                for event in session.scalars(statement)
            ]

    def delete_analysis(self, analysis_id: str) -> None:
        """Delete one analysis; used by test/maintenance callers."""
        with self.session_factory.begin() as session:
            session.execute(
                delete(ReviewEvent).where(ReviewEvent.analysis_id == analysis_id)
            )
            result = session.execute(
                delete(Analysis).where(Analysis.analysis_id == analysis_id)
            )
            if result.rowcount == 0:
                raise KeyError(analysis_id)

    def clear(self) -> None:
        """Clear persistence tables, primarily for isolated automated tests."""
        with self.session_factory.begin() as session:
            session.execute(delete(ReviewEvent))
            session.execute(delete(Analysis))
