import re
import unicodedata
from typing import Dict, Any

# Official writing format validator — opsiyonel entegrasyon.
# Hata durumunda sistemi crash ettirmez.
try:
    from backend.app.official_writing.format_validator import validate_format as _ow_validate
    _OW_VALIDATOR_AVAILABLE = True
except Exception:  # pragma: no cover
    _OW_VALIDATOR_AVAILABLE = False

from backend.app.institutions.profile_loader import (
    load_institution_profile,
    InstitutionProfile,
)

# Yarışma demosunda aktif kurum — RoutingAgent ile aynı
_DEFAULT_INSTITUTION = "kaymakamlik"
_UNVERIFIED_OUTCOME_PATTERNS = (
    r"\bkabul\s+edilmiştir\b",
    r"\bonaylanmıştır\b",
    r"\b(?:başvurunuz\s+)?işleme\s+alınmıştır\b",
    r"\bverilmiştir\b",
    r"\btamamlanmıştır\b",
)
_FAKE_REFERENCE_PATTERNS = (
    r"\b00[./]00[./]0000\b",
    r"\b0{6,}(?:[-/.][0-9A-ZÇĞİÖŞÜ]+)+\b",
    r"\[(?:İLGİ\s+)?(?:TARİHİ|SAYISI)\]",
)
_REFERENCE_CLAIM_PATTERN = (
    r"\b\d{2}[./]\d{2}[./]\d{4}\s+tarihli(?:\s+ve\s+"
    r"[0-9A-ZÇĞİÖŞÜ][0-9A-ZÇĞİÖŞÜ./-]{3,}\s+sayılı)?"
)


def _normalize_claim_text(value: Any) -> str:
    text = str(value or "").replace("I", "ı").replace("İ", "i")
    return unicodedata.normalize("NFKC", text.casefold()).replace("i\u0307", "i")


def find_unverified_outcome_claims(value: Any) -> list[str]:
    text = _normalize_claim_text(value)
    return [
        pattern
        for pattern in _UNVERIFIED_OUTCOME_PATTERNS
        if re.search(pattern, text)
    ]


def find_unverified_reference_claims(
    value: Any,
    extraction: Dict[str, Any] | None = None,
) -> list[str]:
    text = str(value or "")
    matches = [
        pattern
        for pattern in _FAKE_REFERENCE_PATTERNS
        if re.search(pattern, text, re.IGNORECASE)
    ]
    fields = (extraction or {}).get("fields", {})
    date_field = fields.get("document_date", {}) if isinstance(fields, dict) else {}
    number_field = fields.get("document_number", {}) if isinstance(fields, dict) else {}
    date_value = date_field.get("value") if isinstance(date_field, dict) else date_field
    number_value = number_field.get("value") if isinstance(number_field, dict) else number_field
    if (
        (not date_value or not number_value)
        and re.search(_REFERENCE_CLAIM_PATTERN, text, re.IGNORECASE)
    ):
        matches.append(_REFERENCE_CLAIM_PATTERN)
    return list(dict.fromkeys(matches))


class QualityAgent:
    """
    Kalite kontrol ajanı.

    Geçerli birim seti: data/institutions/kaymakamlik/kurum_profili_kaymakamlik.yaml
    unit_registry.json KULLANILMIYOR.

    RoutingAgent ile aynı source-of-truth'u paylaşır.
    """

    def __init__(self, institution: str = _DEFAULT_INSTITUTION):
        self.institution = institution
        self.valid_units: set[str] = set()
        try:
            profile: InstitutionProfile = load_institution_profile(institution)
            for birim in profile.birimler:
                if isinstance(birim, dict) and birim.get("ad"):
                    self.valid_units.add(birim["ad"])
        except (FileNotFoundError, ValueError):
            pass  # fail-safe: valid_units boş kalır, routing check warning verir

    def check_quality(
        self,
        document: Dict[str, Any],
        extraction: Dict[str, Any],
        legal_analysis: Dict[str, Any],
        missing_fields: Dict[str, Any],
        summary: Dict[str, Any],
        routing: Dict[str, Any],
        draft: Dict[str, Any],
        human_review: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        
        result = {
            "status": "pass",
            "checks": {},
            "issues": [],
            "warnings": [],
            "requires_human_review": False
        }

        def add_check(key, status, msg):
            result["checks"][key] = {"status": status, "message": msg}
            if status == "fail":
                result["issues"].append(msg)
                result["status"] = "fail"
                result["requires_human_review"] = True
            elif status == "warning":
                result["warnings"].append(msg)
                if result["status"] != "fail":
                    result["status"] = "warning"

        # 1. document_classification
        if document and document.get("document_type"):
            doc_type = document.get("document_type")
            intent = document.get("process_intent")
            if doc_type == "diger" or intent == "diger":
                add_check("document_classification", "warning", "Sınıflandırma veya işlem niyeti 'diğer' olduğu için personel onayı gerekiyor.")
                result["requires_human_review"] = True
            else:
                add_check("document_classification", "pass", "Evrak sınıflandırması mevcut.")
        else:
            add_check("document_classification", "fail", "Evrak sınıflandırması yapılamadı.")

        # 2. extraction
        if extraction and extraction.get("fields"):
            has_unvalidated = False
            for k, v in extraction.get("fields", {}).items():
                if isinstance(v, dict) and not v.get("evidence"):
                    has_unvalidated = True
            if extraction.get("needs_human_review") or has_unvalidated:
                add_check("extraction", "warning", "Çıkarım sonuçlarında eksik kanıtlı alanlar var veya onay gerekiyor.")
                result["requires_human_review"] = True
            else:
                add_check("extraction", "pass", "Bilgi çıkarımı geçerli.")
        else:
            add_check("extraction", "fail", "Belgeden hiçbir bilgi çıkarılamadı.")

        # 3. missing_fields consistency
        if missing_fields:
            pres = set(missing_fields.get("present_fields", []))
            miss = set(missing_fields.get("missing_fields", []))
            uncert = set(missing_fields.get("uncertain_fields", []))
            
            if pres.intersection(miss) or pres.intersection(uncert) or miss.intersection(uncert):
                add_check("missing_fields_consistency", "fail", "Eksik alan analizi birbiriyle çelişen (hem var hem yok) sonuçlar üretti.")
            elif missing_fields.get("needs_human_review"):
                add_check("missing_fields", "warning", "Eksik alan analizi personel incelemesi gerektiriyor.")
            else:
                add_check("missing_fields", "pass", "Eksik alan kontrolü yapıldı.")
        else:
            add_check("missing_fields", "fail", "Eksik alan analizi bulunamadı.")

        # 4. legal_evidence
        if legal_analysis:
            evidence = legal_analysis.get("evidence", [])
            sources = legal_analysis.get("sources", [])
            
            if evidence:
                add_check("legal_evidence", "pass", "Mevzuat dayanağı kanıtı mevcut.")
            elif sources:
                add_check("legal_evidence", "warning", "Kaynak bulundu ancak doğrulanmış hukuki kanıt çıkarılamadı.")
            else:
                add_check("legal_evidence", "warning", "Doğrulanmış hukuki mevzuat dayanağı bulunamadı.")
        else:
            add_check("legal_evidence", "warning", "Mevzuat analizi mevcut değil.")

        # 5. routing
        rec_unit = routing.get("recommended_unit")
        if routing.get("needs_human_review") or routing.get("ambiguity_reason"):
            add_check("routing", "warning", "Birim yönlendirmesi belirsiz, manuel inceleme gerekiyor.")
            result["requires_human_review"] = True
        elif rec_unit:
            if rec_unit in self.valid_units:
                add_check("routing", "pass", "Önerilen birim sistem kayıtlarında mevcut.")
            else:
                add_check("routing", "fail", f"Önerilen '{rec_unit}' birimi sistem kayıtlarında (registry) bulunamadı.")
        else:
            add_check("routing", "fail", "Hiçbir yönlendirme birimi bulunamadı.")

        # 6. summary consistency
        if summary and extraction:
            struc = summary.get("structured_summary", {})
            ext_fields = extraction.get("fields", {})
            
            s_app = struc.get("applicant", "")
            e_app = ext_fields.get("person_name", {}).get("value", "")
            
            if s_app and e_app and str(s_app) != str(e_app):
                add_check("summary_consistency", "warning", "Özet içindeki başvuru sahibi ile çıkarım eşleşmiyor.")
            elif summary.get("needs_human_review"):
                add_check("summary", "warning", "Özet manuel inceleme gerektiriyor.")
            else:
                add_check("summary", "pass", "Özet tutarlı.")

        # 7. draft grounding
        if draft:
            if draft.get("draft_generation_mode") == "blocked_insufficient_context":
                add_check("draft", "warning", "Eksik bilgi nedeniyle taslak metin oluşturulamadı (Güvenli blokaj).")
                result["requires_human_review"] = True
            elif draft.get("requires_human_approval"):
                add_check("draft", "warning", "Taslak metin personel onayı gerektiriyor.")
            else:
                add_check("draft", "pass", "Taslak metin üretildi.")

            draft_payload = draft.get("draft") if isinstance(draft.get("draft"), dict) else draft
            outcome_claims = find_unverified_outcome_claims(
                draft_payload.get("body", "") if isinstance(draft_payload, dict) else ""
            )
            if outcome_claims:
                add_check(
                    "unverified_outcome_claim",
                    "warning",
                    "Olası doğrulanmamış sonuç iddiası bulundu; taslak insan incelemesine işaretlendi.",
                )
                result["requires_human_review"] = True

            reference_claims = find_unverified_reference_claims(
                draft_payload.get("body", "") if isinstance(draft_payload, dict) else "",
                extraction,
            )
            if reference_claims:
                add_check(
                    "unverified_reference_claim",
                    "warning",
                    "Doğrulanmamış veya sahte görünümlü tarih/referans numarası "
                    "bulundu; taslak insan incelemesine işaretlendi.",
                )
                result["requires_human_review"] = True
                
            # Official Writing check
            off = draft.get("official_render", {})
            if off:
                if off.get("success"):
                    render_missing = off.get("missing_fields", [])
                    if render_missing:
                        add_check(
                            "official_format",
                            "warning",
                            "Resmî taslak önizlemesi oluşturuldu; personel/EBYS "
                            f"tarafından doldurulacak alanlar: {', '.join(render_missing)}.",
                        )
                        result["requires_human_review"] = True
                    else:
                        add_check("official_format", "pass", "Resmî format başarıyla oluşturuldu.")
                elif off.get("attempted"):
                    add_check("official_format", "fail", "Resmî format üretimi sırasında hata oluştu.")
                else:
                    add_check("official_format", "warning", "Resmî format nihai metadata eksik olduğu için tamamlanamadı.")
                    result["requires_human_review"] = True
                    
            # Deterministik form biçim kurallarının kontrolü
            self._check_official_writing_format(draft, add_check, result)
        else:
            add_check("draft", "warning", "Taslak metin mevcut değil.")

        # 8. human_review checks
        if result["requires_human_review"]:
            add_check("human_review", "warning", "Kritik işlemler veya belirsizlikler nedeniyle personel onayı gerekiyor.")
        
        return result

    def _check_official_writing_format(
        self,
        draft: Dict[str, Any],
        add_check,
        result: Dict[str, Any],
    ) -> None:
        """
        Official Writing Format Validator'ı çağırır ve sonucu mevcut
        quality schema'sına adapter ile ekler.

        Yalnızca Writing Agent resmî yazı context'i veya render edilmiş
        resmî yazı ürettiyse (ust_yazi / cevap_yazisi / tekit_yazisi)
        format validation çalışır. Diğer türler atlanır.

        Validator hatası sistemi crash ettirmez; warning/fail üretilir
        ve requires_human_review=True olur.
        """
        if not _OW_VALIDATOR_AVAILABLE:
            return

        if not draft:
            return

        draft_type = draft.get("draft_type") or ""
        # Resmî yazı türü mapping: writing_agent draft_type → validator yazi_turu
        RESMI_YAZI_TURLERI = {
            "ust_yazi": "ust_yazi",
            "bilgilendirme_metni": "ust_yazi",  # Ayrı şablon yok [TASARIM KARARI]
            "cevap_yazisi": "cevap_yazisi",
            "tekit_yazisi": "tekit_yazisi",
        }

        yazi_turu = RESMI_YAZI_TURLERI.get(draft_type)
        if not yazi_turu:
            # eksik_bilgi_talebi, diger → biçimsel format kontrolü uygulanmaz
            return

        # Validation, LLM'in ham draft'ı üzerinden değil, official_render'ın
        # oluşturduğu context üzerinden yapılır. Çünkü şablona geçen veriler bunlardır.
        off_render = draft.get("official_render", {})
        taslak_dict = off_render.get("context")
        
        if not taslak_dict:
            add_check(
                "official_writing_format",
                "warning",
                "Format kontrolü için resmî yazı bağlamı (context) bulunamadı."
            )
            return

        try:
            sonuc = _ow_validate(
                taslak=taslak_dict,
                yazi_turu=yazi_turu,
                missing_fields=off_render.get("missing_fields", []),
            )

            error_msgs = [h.mesaj for h in sonuc.hatalar]
            warning_msgs = [h.mesaj for h in sonuc.uyarilar]

            if not sonuc.gecerli:
                add_check(
                    "official_writing_format",
                    "fail",
                    f"Resmî yazı biçim hataları: {'; '.join(error_msgs[:3])}",
                )
            elif warning_msgs:
                add_check(
                    "official_writing_format",
                    "warning",
                    f"Resmî yazı biçim uyarıları: {'; '.join(warning_msgs[:3])}",
                )
                result["requires_human_review"] = True
            else:
                add_check(
                    "official_writing_format",
                    "pass",
                    "Resmî yazı biçim doğrulaması geçti.",
                )

        except Exception as exc:
            # Validator çökmesi sistemi etkilemez
            add_check(
                "official_writing_format",
                "warning",
                f"Resmî yazı biçim doğrulaması çalışırken hata oluştu: {exc}",
            )
            result["requires_human_review"] = True
