"""Shared CaseEngine singleton bound to the same DATABASE_URL as AnalysisRepository."""

from __future__ import annotations

from backend.app.cases.engine import CaseEngine
from backend.app.db.database import create_session_factory, get_default_engine
from backend.app.db.models import Base

_case_engine: CaseEngine | None = None


def get_case_engine() -> CaseEngine:
    global _case_engine
    if _case_engine is None:
        from backend.app.db import case_models as _case_models  # noqa: F401

        engine = get_default_engine()
        Base.metadata.create_all(engine)
        _case_engine = CaseEngine(engine)
        _case_engine.bootstrap()
    return _case_engine


def reset_case_engine_for_tests() -> None:
    global _case_engine
    if _case_engine is not None:
        _case_engine.clear_domain()
