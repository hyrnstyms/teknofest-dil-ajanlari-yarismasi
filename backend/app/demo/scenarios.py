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

# ---------------------------------------------------------------------------
# 5 GOLDEN DEMO CASES — Faz 4 Jüri Demosu
# ---------------------------------------------------------------------------
# Her senaryo farklı bir lifecycle noktasında başlar:
#   yol_onarim       → READY_TO_ROUTE  (havale bekleyen)   [DEMO FIXTURE]
#   eksik_adres      → WAITING_CITIZEN_INFO (eksik bilgi)   [DEMO FIXTURE]
#   belirsiz_ruhsat  → READY_TO_ROUTE  (belge kontrolü)    [DEMO FIXTURE]
#   cop_temizlik     → RECEIVED        (yeni evrak)         [DEMO FIXTURE]
#   dis_kurum_afet   → READY_TO_ROUTE  (dış kurum)          [DEMO FIXTURE]
# ---------------------------------------------------------------------------
SCENARIOS: dict[str, dict[str, Any]] = {
    # -----------------------------------------------------------------------
    # KAYMAKAMLIK: Okul nakil bilgisi talebi (test coverage — silinmez)
    # -----------------------------------------------------------------------
    "kaymakamlik_egitim": {
        "user_key": "selin_aksoy",
        "title": "Okul Nakil Bilgisi Talebi",
        "originator": "Emine Yıldız",
        "target": "milli_egitim",
        "unit": "İlçe Millî Eğitim Müdürlüğü",
        "summary": "Öğrencinin okul nakil işlemleri için gerekli belgeler hakkında bilgi talebi.",
        "document_type": "dilekce",
        "intent": "bilgi_talebi",
        "source_type": "VATANDAS",
        "priority": "Normal",
        "expected_draft_type": "cevap_yazisi",
    },


    # Kaynak: data/institutions/belediye/ornek_evraklar/02_yol_onarim_talebi.txt
    # Lifecycle: READY_TO_ROUTE (havale kararı bekliyor)
    # -----------------------------------------------------------------------
    "yol_onarim": {
        "user_key": "ayse_kaya",
        "title": "Cumhuriyet Mah. Gül Sokak — Asfalt Çökmesi",
        "originator": "Ayşe Demir",
        "target": "fen_isleri",
        "unit": "Fen İşleri Müdürlüğü",
        "summary": (
            "Cumhuriyet Mahallesi Gül Sokak üzerinde yaklaşık 50 metre uzunluğunda "
            "asfalt çökmesi ve çukur oluşumu tespit edilmiştir. Saha incelemesi "
            "ve bakım programına alınması talep edilmektedir."
        ),
        "document_type": "dilekce",
        "intent": "bildirim",
        "source_type": "VATANDAS",
        "ai_operation": {
            "task_type": "YOL_BAKIM_INCELEME",
            "department_code": "fen_isleri",
            "team_code": "saha_bakim_ekibi",
            "team_name": "Saha Bakım Ekibi",
            "recommended_role": "TEKNIKER",
            "requires_field_visit": True,
            "reason": (
                "Yol çökmesi bildirimi fiziksel saha incelemesi gerektirir. "
                "Fen İşleri Saha Bakım Ekibi yetkili ve kapasiteli birimdir."
            ),
        },
        "priority": "Yüksek",
        "priority_reason": "Yayalar için düşme tehlikesi, olası araç hasarı.",
        "expected_draft_type": "cevap_yazisi",
        "legal_key": "municipal_roads",
    },

    # -----------------------------------------------------------------------
    # CASE 2: Aynı tip ama konum / adres eksik — eksik bilgi vatandaştan istenir
    # Kaynak: Sentetik — 13_ambiguous_ruhsat ile 02_yol_onarim_talebi'nin birleşimi
    # Lifecycle: WAITING_CITIZEN_INFO (citizen eksik bilgi yanıtı bekleniyor)
    # -----------------------------------------------------------------------
    "yol_onarim_yedek": {
        "user_key": "ayse_kaya", "title": "Örnek Demo Verisi — Yol Onarım Cevabı",
        "originator": "Ayşe Demir", "target": "fen_isleri", "unit": "Fen İşleri Müdürlüğü",
        "summary": "Cumhuriyet Mahallesi Gül Sokak yol yüzeyindeki deformasyonun incelenmesi ve bakım programına alınması talebi.",
        "document_type": "dilekce", "intent": "bildirim", "source_type": "VATANDAS",
        "priority": "Normal", "expected_draft_type": "cevap_yazisi", "legal_key": "municipal_roads", "stage": "late",
    },
    "tamamlanmis_dosya": {
        "user_key": "ayse_kaya", "title": "Örnek Demo Verisi — Sonuçlanmış Yol Başvurusu",
        "originator": "Mert Yılmaz", "target": "fen_isleri", "unit": "Fen İşleri Müdürlüğü",
        "summary": "Çınar Sokak yol yüzeyindeki deformasyona ilişkin sonuçlandırılan başvuru.",
        "document_type": "dilekce", "intent": "bildirim", "source_type": "VATANDAS",
        "priority": "Normal", "expected_draft_type": "cevap_yazisi", "legal_key": "municipal_roads", "stage": "completed",
    },
    "eksik_adres": {
        "user_key": "ayse_kaya",
        "title": "Kaldırım Çökmesi — Konum Eksik",
        "originator": "Can Kaya",
        "target": None,
        "unit": None,
        "summary": (
            "Başvuruda kaldırım çöktüğü bildirilmiş ancak işlem yapılacak açık adres "
            "belirtilmemiştir. Saha incelemesi için konum bilgisi zorunludur."
        ),
        "document_type": "dilekce",
        "intent": "bildirim",
        "source_type": "VATANDAS",
        "clarification": True,
        "clarification_field": "location",
        "clarification_target_type": "VATANDAS",
        "clarification_reason": "Saha incelemesi yapılamaz: olay yeri belirtilmemiş.",
        "clarification_recommended_action": "REQUEST_INFORMATION",
        "clarification_question": "Kaldırımın çöktüğü sokak veya konum bilgisini belirtir misiniz?",
        "priority": "Normal",
        "expected_draft_type": "MISSING_INFORMATION_REQUEST",
    },

    # -----------------------------------------------------------------------
    # CASE 3: Ruhsat başvurusu — Zabıta → Belge Kontrolü
    # Kaynak: data/institutions/belediye/ornek_evraklar/01_ruhsat_basvurusu.txt
    # Lifecycle: READY_TO_ROUTE (AI önerisi: Zabıta/İmar, insan kararı bekliyor)
    # -----------------------------------------------------------------------
    "belirsiz_ruhsat": {
        "user_key": "ayse_kaya",
        "title": "İşyeri Ruhsat Türü Belirsiz Başvuru",
        "originator": "Zeynep Acar",
        "target": "zabita",
        "unit": "Zabıta Müdürlüğü",
        "summary": (
            "Atatürk Caddesi No:14 adresindeki unlu mamüller satış ve üretim işyeri için "
            "ruhsat başvurusu. Başvurunun yapı ruhsatı mı işyeri ruhsatı mı olduğu belirtilmemiş; "
            "belge kontrolü ve uygun birim tespiti gerekiyor."
        ),
        "document_type": "ruhsat_basvurusu",
        "intent": "basvuru",
        "source_type": "VATANDAS",
        "clarification": True,
        "clarification_field": "permit_type",
        "clarification_question": "Başvurunuz hangi ruhsat türüyle ilgilidir?",
        "clarification_question_type": "single_choice",
        "clarification_options": [{"value": "YAPI_RUHSATI", "label": "Yapı Ruhsatı"}, {"value": "ISYERI_RUHSATI", "label": "İşyeri Açma ve Çalışma Ruhsatı"}],
        "extra_fields": {"address": {"value": "Atatürk Caddesi No:14", "validated": True}, "request": {"value": "Ruhsat başvurusunun değerlendirilmesi", "validated": True}},
        "ai_operation": {
            "task_type": "BELGE_KONTROLU",
            "department_code": "zabita",
            "team_code": "ruhsat_inceleme",
            "team_name": "İşyeri Ruhsat İnceleme Ekibi",
            "recommended_role": "RUHSAT_INCELEME_UZMANI",
            "requires_field_visit": False,
            "reason": (
                "İşyeri açma ve çalışma ruhsatı zabıta yetkisindedir. "
                "Önce belge kontrolü yapılacak, ardından yerinde denetim programlanabilir."
            ),
        },
        "priority": "Normal",
        "expected_draft_type": "cevap_yazisi",
    },

    # -----------------------------------------------------------------------
    # CASE 4: Temizlik / çöp şikayeti — Temizlik İşleri → Saha Ekibi
    # Kaynak: data/institutions/belediye/ornek_evraklar/06_cop_toplama_sikayet.txt
    # Lifecycle: RECEIVED (yeni evrak — demo akışının en başı)
    # -----------------------------------------------------------------------
    "cop_temizlik": {
        "user_key": "ayse_kaya",
        "title": "Meydan Mah. Papatya Sokak — Çöp Toplama Düzensizliği",
        "originator": "Hatice Öztürk",
        "target": "temizlik_isleri",
        "unit": "Temizlik İşleri Müdürlüğü",
        "summary": (
            "Meydan Mahallesi Papatya Sokak'ta son iki haftadır düzenli çöp toplama "
            "hizmetinin yerine getirilmediği bildirilmiştir. Atık birikmesi nedeniyle "
            "kötü koku ve sinek üremesi halk sağlığı sorunu oluşturmaktadır. "
            "Temizlik İşleri Saha Ekibinin ivediyle müdahalesi talep edilmektedir."
        ),
        "document_type": "dilekce",
        "intent": "sikayet",
        "source_type": "VATANDAS",
        "ai_operation": {
            "task_type": "SAHA_EKIBI",
            "department_code": "temizlik_isleri",
            "team_code": "temizlik_saha_ekibi",
            "team_name": "Temizlik Saha Ekibi",
            "recommended_role": "SAHA_EKIBI",
            "requires_field_visit": True,
            "reason": (
                "Çöp toplama hizmet kesintisi saha müdahalesi gerektirir. "
                "Temizlik İşleri Müdürlüğü yetkili birimdir."
            ),
        },
        "priority": "Yüksek",
        "priority_reason": "Halk sağlığı riski (kötü koku, sinek üremesi).",
        "expected_draft_type": "cevap_yazisi",
    },

    # -----------------------------------------------------------------------
    # CASE 5: Dış kurumdan gelen resmi yazı — source_type=DIS_KURUM
    # Kaynak: data/institutions/belediye/ornek_evraklar/09_kurumlar_arasi_afet_koordinasyon.txt
    # Lifecycle: READY_TO_ROUTE (Fen İşlerine / İmar'a havale edilecek)
    # Eksik bilgi varsa: gönderen kuruma (Kaymakamlık) dön, vatandaşa değil
    # -----------------------------------------------------------------------
    "dis_kurum_afet": {
        "user_key": "ayse_kaya",
        "title": "Kaymakamlık — Afet Eylem Planı Altyapı Bilgisi Talebi",
        "originator": "Örenli İlçe Kaymakamlığı",
        "target": "fen_isleri",
        "unit": "Fen İşleri Müdürlüğü",
        "summary": (
            "Örenli Kaymakamlığı, 2026–2027 Afet Eylem Planı güncellemesi kapsamında "
            "belediye yetki alanındaki altyapı bilgilerini (yol, köprü, istinat duvarı, "
            "içme suyu şebekesi) ve mevcut afet toplanma alanlarına ait güncel verileri "
            "talep etmiştir. Son teslim tarihi: 30.08.2026."
        ),
        "document_type": "kurumlar_arasi_yazi",
        "intent": "bilgi_talebi",
        "source_type": "DIS_KURUM",
        "source_channel": "KEP",
        "clarification": True,
        "clarification_field": "permit_type",
        "clarification_question": "Başvurunuz hangi ruhsat türüyle ilgilidir?",
        "clarification_question_type": "single_choice",
        "clarification_options": [{"value": "YAPI_RUHSATI", "label": "Yapı Ruhsatı"}, {"value": "ISYERI_RUHSATI", "label": "İşyeri Açma ve Çalışma Ruhsatı"}],
        "extra_fields": {"address": {"value": "Atatürk Caddesi No:14", "validated": True}, "request": {"value": "Ruhsat başvurusunun değerlendirilmesi", "validated": True}},
        "ai_operation": {
            "task_type": "GENEL_INCELEME",
            "department_code": "fen_isleri",
            "team_code": "saha_bakim_ekibi",
            "team_name": "Saha Bakım Ekibi",
            "recommended_role": "INSAAT_MUHENDISI",
            "requires_field_visit": False,
            "reason": (
                "Kurumlar arası resmi yazı — Kaymakamlık altyapı verisi talep ediyor. "
                "Fen İşleri altyapı kayıtlarına sahip yetkili birimdir. "
                "Eksik bilgi varsa yanıt Kaymakamlığa (gönderen kuruma) iletilmeli; "
                "vatandaşa değil."
            ),
        },
        "priority": "Yüksek",
        "priority_reason": "Yasal teslim tarihi: 30.08.2026.",
        "expected_draft_type": "ust_yazi",
        # Eğer eksik bilgi gerekse → gönderen kuruma (DIS_KURUM) dön
        "missing_info_target_type": "DIS_KURUM",
        "missing_info_target_name": "Örenli İlçe Kaymakamlığı",
    },
}


def demo_enabled() -> bool:
    return os.getenv("DEMO_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}


def _user(key: str) -> CurrentUser:
    p = DEMO_USERS[key]
    return CurrentUser(id=p.id, name=p.name, role=p.role, institution_id=p.institution_id, department_code=p.department_code, user_key=p.user_key)


def _build_clarification(spec: dict[str, Any], key: str) -> dict[str, Any]:
    """Build clarification payload from spec, with target_type support."""
    field = spec.get("clarification_field", "location")
    target_type = spec.get("clarification_target_type", "VATANDAS")
    reason = spec.get("clarification_reason", "Sürecin devamı için eksik bilgi gereklidir.")
    action = spec.get("clarification_recommended_action", "REQUEST_INFORMATION")
    question = spec.get("clarification_question", "Eksik bilgiyi belirtir misiniz?")
    return {
        "needs_clarification": True,
        "blocking": True,
        "requested_fields": [field],
        "question_type": spec.get("clarification_question_type", "free_text"),
        "question": question,
        "options": spec.get("clarification_options", []),
        "resume_target": "MISSING_FIELD",
        "reason": reason,
        "target_type": target_type,
        "target_name": spec.get("clarification_target_name"),
        "target_department": spec.get("clarification_target_department"),
        "recommended_action": action,
        "required_for_process": True,
        "missing_field": field,
    }


LEGAL_EVIDENCE = {
    "municipal_roads": {
        "verified": True,
        "text": "Mahallî müşterek ihtiyaçların karşılanması belediyelerin görev alanındadır.",
        "evidence": [{
            "evidence": "Mahalli idareler, mahalli müşterek ihtiyaçları karşılamak üzere kurulan kamu tüzelkişileridir.",
            "source": "K1",
            "relationship": "Yol bakım talebi mahallî müşterek altyapı hizmeti olduğundan belediye görev alanıyla ilişkilidir.",
        }],
        "sources": [{
            "title": "Türkiye Cumhuriyeti Anayasası", "law_number": "2709", "madde_no": "127",
            "url": "https://www.mevzuat.gov.tr/MevzuatMetin/1.5.2709.pdf",
            "text": "Mahalli idareler; il, belediye veya köy halkının mahalli müşterek ihtiyaçlarını karşılamak üzere kurulan kamu tüzelkişileridir.",
            "trusted_source": True, "rag_eligible": True,
        }],
    }
}

class DemoScenarioService:
    def __init__(self): self.engine = get_case_engine()

    def list(self, institution_id: str | None = None) -> list[dict[str, Any]]:
        return [
            {
                "key": key,
                "title": spec["title"],
                "institution_id": DEMO_USERS[spec["user_key"]].institution_id,
                "prepared": self._existing(key) is not None,
                # Expose expected outcomes for UI labelling
                "expected_department": spec.get("unit"),
                "source_type": spec.get("source_type", "VATANDAS"),
            }
            for key, spec in SCENARIOS.items()
            if institution_id is None or DEMO_USERS[spec["user_key"]].institution_id == institution_id
        ]

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

        spec = SCENARIOS[key]
        user = _user(spec["user_key"])
        analysis_id = f"demo-analysis-{key}-{uuid.uuid4().hex[:8]}"

        # Save minimal analysis identity first (FK ordering for PostgreSQL)
        AnalysisRepository(engine=self.engine.engine).save_analysis(analysis_id, {
            "analysis_id": analysis_id,
            "institution_id": user.institution_id,
            "is_demo": True,
            "demo_scenario_key": key,
        })

        source_type = spec.get("source_type", "VATANDAS")
        source_channel = spec.get("source_channel", "EBYS")

        created = self.engine.create_case(
            user,
            {
                "confirmed": True,
                "source_type": source_type,
                "source_channel": source_channel,
                "originator_type": source_type,
                "originator_name": spec["originator"],
                "analysis_id": analysis_id,
                "priority": f"{DEMO_PREFIX}{key}",
                "received_at": datetime.now(timezone.utc),
            },
            raw_citizen_token=self.token(key),
        )
        self.engine.mark_analysis_started(created["id"], user)

        blocking = bool(spec.get("clarification"))
        clarification = _build_clarification(spec, key) if blocking else {}

        ai_op = spec.get("ai_operation", {})
        routing = {} if blocking else {
            "recommended_unit": spec["unit"],
            "recommended_department_code": spec["target"],
            "reason": ai_op.get("reason") or "Belgedeki konu ve kurum profilindeki görev alanı eşleşmektedir.",
            "evidence": [spec["summary"]] + (["2709 sayılı Türkiye Cumhuriyeti Anayasası, Madde 127"] if spec.get("legal_key") == "municipal_roads" else []),
            "alternatives": [],
            "requires_human_review": True,
        }

        # Priority assessment
        priority_val = spec.get("priority", "Normal")
        priority_reason = spec.get("priority_reason", "")
        priority_assessment = {
            "priority": "HIGH" if priority_val in ("Yüksek", "Acil") else "MEDIUM" if priority_val == "Normal" else "LOW",
            "priority_rule": "demo_scenario",
            "priority_reason": priority_reason,
            "decision_source": "demo_fixture",
        }

        state = {
            "analysis_id": analysis_id,
            "case_id": created["id"],
            "tracking_code": created["tracking_code"],
            "institution_id": user.institution_id,
            "kurum_profili_id": user.institution_id,
            "raw_text": spec["summary"],
            "document": {
                "document_type": spec["document_type"],
                "process_intent": spec["intent"],
                "subject_excerpt": spec["title"],
            },
            "extraction": {
                "fields": {
                    "person_name": {"value": spec["originator"], "validated": True},
                    "subject": {"value": spec["title"], "validated": True},
                    **spec.get("extra_fields", {}),
                }
            },
            "missing_fields": {
                "has_blocking_missing": blocking,
                "blocking_fields": clarification.get("requested_fields", []),
                "missing_fields": clarification.get("requested_fields", []),
            },
            "summary": {
                "short_summary": spec["summary"],
                "structured_summary": {"subject": spec["title"], "request": spec["summary"]},
            },
            "legal_analysis": LEGAL_EVIDENCE.get(spec.get("legal_key"), {"verified": False, "evidence": [], "sources": []}),
            "routing": routing,
            "clarification": clarification,
            "ai_operation": ai_op if ai_op else {},
            "operational_priority": priority_assessment,
            "case_orchestration": {
                "blocking_missing": blocking,
                "routing": routing,
                "clarification": clarification,
                "ai_operation": ai_op if ai_op else {},
            },
            "human_review": {"required": True, "status": "pending_review"},
            "is_demo": True,
            "demo_scenario_key": key,
        }
        AnalysisRepository(engine=self.engine.engine).save_analysis(analysis_id, state)
        completed = self.engine.mark_analysis_completed(created["id"], user, ready_to_route=not blocking)
        if blocking:
            self.engine.create_citizen_request(user, created["id"], clarification, completed["version"], True)

        if spec.get("stage") in {"late", "completed"}:
            current = self.engine.route_case(user, created["id"], department_code=spec["target"], expected_version=completed["version"], confirmed=True, reason="Örnek demo verisi", routing_snapshot={"demo": True})
            worker = _user("mehmet_demir")
            current = self.engine.start_case(worker, created["id"], current["version"], True)
            action = self.engine.record_department_action(worker, created["id"], {
                "action_type": "Saha İncelemesi", "result": "Yol yüzeyinde deformasyon tespit edildi.",
                "decision": "Bölge bakım programına alındı.", "notes": "Örnek demo verisi",
            }, current["version"], True)
            from backend.app.cases.auto_draft import generate_official_response_after_action
            generated = generate_official_response_after_action(engine=self.engine, user=worker, case_id=created["id"], action_result=action)
            aggregate = self.engine.get_case_aggregate(worker, created["id"])
            draft = aggregate["drafts"][-1]
            edited_body = draft["content"]["body"]
            edited = self.engine.save_draft(worker, created["id"], draft_type="OFFICIAL_RESPONSE", content={**draft["content"], "body": edited_body}, grounded_action_id=draft["grounded_action_id"], expected_version=aggregate["case"]["version"], confirmed=True)
            approved = self.engine.approve_draft(worker, created["id"], edited["draft"]["id"], edited["case"]["version"], True)
            if spec.get("stage") == "completed":
                self.engine.complete_case(worker, created["id"], edited["draft"]["id"], approved["case"]["version"], True)

        return self._result(self._existing(key), key, created=True)

    def _result(self, case: CaseRecord | None, key: str, *, created: bool) -> dict[str, Any]:
        assert case is not None
        spec = SCENARIOS[key]
        return {
            "scenario_key": key,
            "created": created,
            "case": self.engine.serialize_case(case),
            "citizen_url": f"/takip/{case.tracking_code}?token={self.token(key)}",
            "citizen_token": self.token(key),
            # Extra demo metadata for UI display
            "demo_meta": {
                "title": spec["title"],
                "source_type": spec.get("source_type", "VATANDAS"),
                "document_type": spec["document_type"],
                "intent": spec["intent"],
                "expected_department": spec.get("unit"),
                "expected_task": spec.get("ai_operation", {}).get("task_type"),
                "expected_team": spec.get("ai_operation", {}).get("team_name"),
                "requires_field_visit": spec.get("ai_operation", {}).get("requires_field_visit"),
                "priority": spec.get("priority"),
                "expected_draft_type": spec.get("expected_draft_type"),
                "is_dis_kurum": spec.get("source_type") == "DIS_KURUM",
            },
        }

    def reset(self) -> dict[str, int]:
        with self.engine.session_factory.begin() as session:
            rows = list(session.scalars(select(CaseRecord).where(CaseRecord.priority.like(f"{DEMO_PREFIX}%"))))
            ids = [row.id for row in rows]
            analysis_ids = [row.analysis_id for row in rows if row.analysis_id]
            if ids:
                # Idempotency rows have no case_id FK — only remove ones referencing our demo cases
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
