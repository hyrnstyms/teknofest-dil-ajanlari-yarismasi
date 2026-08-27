from datetime import datetime
import os
import uuid

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError

from backend.app.db.models import Analysis
from backend.app.db.repository import AnalysisRepository


@pytest.fixture
def repository(tmp_path):
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        repo = AnalysisRepository(
            database_url=(
                f"sqlite:///{(tmp_path / 'analyses.sqlite3').as_posix()}"
            )
        )
        yield repo
        repo.engine.dispose()
        return

    schema = f"test_analysis_repository_{uuid.uuid4().hex}"
    admin_engine = create_engine(database_url)
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    test_engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"options": f"-csearch_path={schema}"},
    )
    repo = AnalysisRepository(engine=test_engine)
    try:
        yield repo
    finally:
        test_engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def _state(analysis_id: str = "analysis-1") -> dict:
    return {
        "analysis_id": analysis_id,
        "kurum_profili_id": "kaymakamlik_v1",
        "document": {
            "document_type": "dilekce",
            "process_intent": "bilgi_talebi",
        },
        "routing": {"recommended_unit": "Yazı İşleri"},
        "human_review": {"required": True, "status": "pending_review"},
        "draft": None,
        "nested": {"items": [1, {"when": datetime(2026, 8, 26, 12, 0)}]},
        "created_at": "2026-08-26T12:00:00",
    }


def test_create_read_and_json_round_trip(repository):
    state = _state()
    repository.save_analysis("analysis-1", state)

    stored = repository.get_analysis("analysis-1")

    assert stored is not None
    assert stored["draft"] is None
    assert stored["kurum_profili_id"] == "kaymakamlik_v1"
    assert stored["nested"] == {
        "items": [1, {"when": "2026-08-26 12:00:00"}]
    }
    with repository.session_factory() as session:
        row = session.scalar(
            select(Analysis).where(Analysis.analysis_id == "analysis-1")
        )
        assert row is not None
        assert row.institution_id == "kaymakamlik_v1"


def test_turkish_unicode_round_trip(repository):
    state = _state("turkish-unicode")
    state["document"]["subject_excerpt"] = "Çığ, şüphe, ılık göl ve üzüm"
    state["draft"] = {
        "subject": "Türkçe karakter doğrulaması",
        "body": "ç, ş, ğ, ı, ö, ü ve büyükleri Ç, Ş, Ğ, İ, Ö, Ü",
    }

    repository.save_analysis("turkish-unicode", state)
    stored = repository.get_analysis("turkish-unicode")

    assert stored is not None
    assert stored["document"]["subject_excerpt"] == "Çığ, şüphe, ılık göl ve üzüm"
    assert stored["draft"] == state["draft"]


def test_list_analyses_and_pending_reviews(repository):
    repository.save_analysis("pending", _state("pending"))
    approved = _state("approved")
    approved["human_review"]["status"] = "approved"
    repository.save_analysis("approved", approved)

    assert {item["analysis_id"] for item in repository.list_analyses()} == {
        "pending",
        "approved",
    }
    assert [item["analysis_id"] for item in repository.list_analyses(status="approved")] == [
        "approved"
    ]
    assert [item["analysis_id"] for item in repository.list_pending_reviews()] == [
        "pending"
    ]


def test_list_analyses_filters_by_institution_and_keeps_unfiltered_compatibility(repository):
    kaymakamlik = _state("kaymakamlik-analysis")
    belediye = _state("belediye-analysis")
    belediye["kurum_profili_id"] = "belediye"
    repository.save_analysis("kaymakamlik-analysis", kaymakamlik)
    repository.save_analysis("belediye-analysis", belediye)

    assert {item["analysis_id"] for item in repository.list_analyses()} == {
        "kaymakamlik-analysis",
        "belediye-analysis",
    }
    assert [
        item["analysis_id"]
        for item in repository.list_analyses(institution_id="kaymakamlik_v1")
    ] == ["kaymakamlik-analysis"]
    assert [
        item["analysis_id"]
        for item in repository.list_analyses(institution_id="belediye")
    ] == ["belediye-analysis"]


def test_review_event_is_recorded_with_state_update(repository):
    state = _state()
    repository.save_analysis("analysis-1", state)
    state["human_review"]["status"] = "approved"

    repository.update_analysis_with_event(
        "analysis-1", state, "approve", {"source": "review-endpoint"}
    )

    events = repository.list_review_events("analysis-1")
    assert len(events) == 1
    assert events[0]["action"] == "approve"
    assert events[0]["payload"] == {"source": "review-endpoint"}
    assert repository.get_analysis("analysis-1")["human_review"]["status"] == "approved"


def test_state_update_rolls_back_when_review_event_insert_fails(repository):
    state = _state()
    repository.save_analysis("analysis-1", state)
    state["human_review"]["status"] = "approved"

    with pytest.raises(IntegrityError):
        repository.update_analysis_with_event(
            "analysis-1",
            state,
            None,  # type: ignore[arg-type] -- deliberately violates NOT NULL
            {},
        )

    stored = repository.get_analysis("analysis-1")
    assert stored is not None
    assert stored["human_review"]["status"] == "pending_review"
    assert repository.list_review_events("analysis-1") == []


def test_restart_simulation_reads_from_second_engine(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'restart.sqlite3').as_posix()}"
    first = AnalysisRepository(database_url=database_url)
    first.save_analysis("survives-restart", _state("survives-restart"))
    first.engine.dispose()

    second = AnalysisRepository(database_url=database_url)
    try:
        stored = second.get_analysis("survives-restart")
        assert stored is not None
        assert stored["analysis_id"] == "survives-restart"
        assert stored["draft"] is None
    finally:
        second.engine.dispose()
