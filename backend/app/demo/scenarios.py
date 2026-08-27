from __future__ import annotations
import os
import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import delete, select
from backend.app.auth.dependencies import CurrentUser
from backend.app.auth.principals import DEMO_USERS
from backend.app.cases.runtime import get_case_engine
from backend.app.db.case_models import CaseAssignment, CaseDraft, CaseEvent, CaseIdempotencyKey, CaseNotification, CaseRecord, CitizenRequest, DepartmentAction
from backend.app.db.models import Analysis, ReviewEvent
from backend.app.db.repository import AnalysisRepository

DEMO_PREFIX = "DEMO:"
SCENARIOS: dict[str, dict[str, Any]] = {
    "yol_onarim": {"user_key": "ayse_kaya", "title": "Yol Onarım Talebi", "originator": "Ali Yılmaz", "target": "fen_isleri", "unit": "Fen İşleri Müdürlüğü", "summary": "Çınar Mahallesi Gül Sokak yol deformasyonunun incelenmesi ve bakım programına alınması talebi.", "document_type": "dilekce", "intent": "bildirim"},
    "belirsiz_ruhsat": {"user_key": "ayse_kaya", "title": "Ruhsat Türü Belirsiz Başvuru", "originator": "Zeynep Acar", "target": None, "unit": None, "summary": "Başvuruda yalnız ruhsat ifadesi bulunduğu için güvenli birim seçimi yapılamadı.", "document_type": "dilekce", "intent": "basvuru", "clarification": True},
    "kaymakamlik_egitim": {"user_key": "selin_aksoy", "title": "Okul Nakil Bilgisi Talebi", "originator": "Emine Yıldız", "target": "milli_egitim", "unit": "İlçe Millî Eğitim Müdürlüğü", "summary": "Öğrencinin okul nakil işlemleri için gerekli belgeler hakkında bilgi talebi.", "document_type": "dilekce", "intent": "bilgi_talebi"},
    "eksik_adres": {"user_key": "ayse_kaya", "title": "Konumu Eksik Bakım Başvurusu", "originator": "Can Kaya", "target": None, "unit": None, "summary": "Bakım talebinde işlem yapılacak açık adres belirtilmemiştir.", "document_type": "dilekce", "intent": "bildirim", "clarification": True},
}

def demo_enabled() -> bool:
    return os.getenv("DEMO_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}

def _user(key: str) -> CurrentUser:
    p = DEMO_USERS[key]
    return CurrentUser(id=p.id, name=p.name, role=p.role, institution_id=p.institution_id, department_code=p.department_code, user_key=p.user_key)

class DemoScenarioService:
    def __init__(self): self.engine = get_case_engine()

    def list(self, institution_id: str | None = None) -> list[dict[str, Any]]:
        return [{"key": key, "title": spec["title"], "institution_id": DEMO_USERS[spec["user_key"]].institution_id, "prepared": self._existing(key) is not None} for key, spec in SCENARIOS.items() if institution_id is None or DEMO_USERS[spec["user_key"]].institution_id == institution_id]

    def _existing(self, key: str) -> CaseRecord | None:
        with self.engine.session_factory() as session:
            return session.scalar(select(CaseRecord).where(CaseRecord.priority == f"{DEMO_PREFIX}{key}"))

    @staticmethod
    def token(key: str) -> str: return f"evrag-demo-citizen-{key}"

    def prepare(self, key: str, institution_id: str | None = None) -> dict[str, Any]:
        if key not in SCENARIOS: raise KeyError(key)
        if institution_id and DEMO_USERS[SCENARIOS[key]["user_key"]].institution_id != institution_id: raise PermissionError(key)
        existing = self._existing(key)
        if existing:
            return self._result(existing, key, created=False)
        spec = SCENARIOS[key]; user = _user(spec["user_key"]); analysis_id = f"demo-analysis-{key}-{uuid.uuid4().hex[:8]}"
        created = self.engine.create_case(user, {"confirmed": True, "source_type": "VATANDAS", "source_channel": "EBYS", "originator_type": "VATANDAS", "originator_name": spec["originator"], "analysis_id": analysis_id, "priority": f"{DEMO_PREFIX}{key}", "received_at": datetime.now(timezone.utc)}, raw_citizen_token=self.token(key))
        self.engine.mark_analysis_started(created["id"], user)
        blocking = bool(spec.get("clarification"))
        clarification = {"needs_clarification": True, "blocking": True, "requested_fields": ["permit_type" if key == "belirsiz_ruhsat" else "location"], "question_type": "choice" if key == "belirsiz_ruhsat" else "free_text", "question": "Başvurunuz hangi ruhsat türüyle ilgilidir?" if key == "belirsiz_ruhsat" else "İşlem yapılacak açık adresi belirtir misiniz?", "options": [{"value": "YAPI_RUHSATI", "label": "Yapı ruhsatı"}, {"value": "ISYERI_RUHSATI", "label": "İşyeri açma ve çalışma ruhsatı"}] if key == "belirsiz_ruhsat" else [], "resume_target": "MISSING_FIELD"} if blocking else {}
        routing = {} if blocking else {"recommended_unit": spec["unit"], "recommended_department_code": spec["target"], "reason": "Belgedeki konu ve kurum profilindeki görev alanı eşleşmektedir.", "evidence": [spec["summary"]], "alternatives": [], "requires_human_review": True}
        state = {"analysis_id": analysis_id, "case_id": created["id"], "tracking_code": created["tracking_code"], "institution_id": user.institution_id, "kurum_profili_id": user.institution_id, "raw_text": spec["summary"], "document": {"document_type": spec["document_type"], "process_intent": spec["intent"], "subject_excerpt": spec["title"]}, "extraction": {"fields": {"person_name": {"value": spec["originator"], "validated": True}, "subject": {"value": spec["title"], "validated": True}}}, "missing_fields": {"has_blocking_missing": blocking, "blocking_fields": clarification.get("requested_fields", []), "missing_fields": clarification.get("requested_fields", [])}, "summary": {"short_summary": spec["summary"], "structured_summary": {"subject": spec["title"], "request": spec["summary"]}}, "legal_analysis": {"verified": False, "evidence": [], "sources": []}, "routing": routing, "clarification": clarification, "case_orchestration": {"blocking_missing": blocking, "routing": routing, "clarification": clarification}, "human_review": {"required": True, "status": "pending_review"}, "is_demo": True, "demo_scenario_key": key}
        AnalysisRepository(engine=self.engine.engine).save_analysis(analysis_id, state)
        completed = self.engine.mark_analysis_completed(created["id"], user, ready_to_route=not blocking)
        if blocking:
            self.engine.create_citizen_request(user, created["id"], clarification, completed["version"], True)
        return self._result(self._existing(key), key, created=True)

    def _result(self, case: CaseRecord | None, key: str, *, created: bool) -> dict[str, Any]:
        assert case is not None
        return {"scenario_key": key, "created": created, "case": self.engine.serialize_case(case), "citizen_url": f"/takip/{case.tracking_code}?token={self.token(key)}", "citizen_token": self.token(key)}

    def reset(self) -> dict[str, int]:
        with self.engine.session_factory.begin() as session:
            rows = list(session.scalars(select(CaseRecord).where(CaseRecord.priority.like(f"{DEMO_PREFIX}%"))))
            ids = [row.id for row in rows]; analysis_ids = [row.analysis_id for row in rows if row.analysis_id]
            if ids:
                # Idempotency rows deliberately have no case_id FK. Remove only
                # rows whose stored response identifies one of our tagged demo
                # cases; never touch unrelated user operations.
                idempotency_rows = list(session.scalars(select(CaseIdempotencyKey)))
                for row in idempotency_rows:
                    response = row.response_json or {}
                    response_case = response.get("case") if isinstance(response, dict) else None
                    referenced_id = (
                        response.get("id") if isinstance(response, dict) else None
                    ) or (
                        response_case.get("id") if isinstance(response_case, dict) else None
                    )
                    if referenced_id in ids:
                        session.delete(row)
                for model in (CaseNotification, CaseDraft, DepartmentAction, CitizenRequest, CaseEvent, CaseAssignment):
                    session.execute(delete(model).where(model.case_id.in_(ids)))
                session.execute(delete(CaseRecord).where(CaseRecord.id.in_(ids)))
            if analysis_ids:
                session.execute(delete(ReviewEvent).where(ReviewEvent.analysis_id.in_(analysis_ids)))
                session.execute(delete(Analysis).where(Analysis.analysis_id.in_(analysis_ids)))
        return {"deleted_demo_cases": len(ids)}
