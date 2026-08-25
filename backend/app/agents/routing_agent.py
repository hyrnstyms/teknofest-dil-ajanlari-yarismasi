import re
from typing import Dict, Any

from backend.app.institutions.profile_loader import (
    load_institution_profile,
    InstitutionProfile,
)

# Yarışma demosunda aktif kurum
_DEFAULT_INSTITUTION = "kaymakamlik"


def normalize_turkish_text(text: str) -> str:
    if not text:
        return ""
    trans = str.maketrans("IİÖÜÇĞŞ", "ıiöüçğş")
    text = text.translate(trans).lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


class RoutingAgent:
    """
    Deterministic, açıklanabilir kural tabanlı yönlendirme ajanı.

    Kaynak: data/institutions/kaymakamlik/kurum_profili_kaymakamlik.yaml
    unit_registry.json KULLANILMIYOR.

    V2 Özellikleri:
      - score_breakdown (her kural adımı açıklanıyor)
      - ranked_units Top-3
      - alternative_units
      - ambiguity detection
      - needs_human_review
      - rule_margin semantics
    """

    def __init__(self, institution: str = _DEFAULT_INSTITUTION):
        self.institution = institution
        self._profile_source = (
            f"data/institutions/{institution}/kurum_profili_{institution}.yaml"
        )
        try:
            self._profile: InstitutionProfile = load_institution_profile(institution)
        except Exception:
            self._profile = None

        self._units = []
        self._doc_type_mapping = {}

        if self._profile:
            self._units = self._parse_units(self._profile)
            self._doc_type_mapping = self._parse_doc_types(self._profile)

    def _parse_units(self, profile: InstitutionProfile) -> list[dict]:
        units = []
        for birim in profile.birimler:
            if not isinstance(birim, dict):
                continue
            units.append({
                "unit_id": birim.get("id", ""),
                "name": birim.get("ad", ""),
                "keywords": birim.get("anahtar_kelimeler", []),
                "supported_intents": birim.get("supported_intents", []),
            })
        return units

    def _parse_doc_types(self, profile: InstitutionProfile) -> dict[str, list[str]]:
        mapping = {}
        for ev in profile.evrak_turleri:
            if isinstance(ev, dict):
                mapping[ev.get("id")] = ev.get("tipik_hedef_birim", [])
        return mapping

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(
        self,
        document_type: str,
        process_intent: str,
        subject: str,
        request_text: str,
        extracted_fields: Dict[str, Any],
    ) -> Dict[str, Any]:

        result: Dict[str, Any] = {
            "recommended_unit": None,
            "alternative_units": [],
            "ranked_units": [],
            "reason": None,
            "evidence": [],
            "routing_score": 0.0,
            "score_type": "rule_match",
            "score_breakdown": {
                "intent_score": 0,
                "keyword_score": 0,
                "doc_type_score": 0,
                "details": []
            },
            "registry_source": self._profile_source,
            "needs_human_review": False,
            "warnings": [],
        }

        units = self._units
        if not units:
            result["needs_human_review"] = True
            result["warnings"].append(
                f"Kurum profili yüklenemedi: {self._profile_source}"
            )
            result["reason"] = (
                "Belgenin yönlendirileceği uygun birim güvenilir şekilde "
                "belirlenemedi (profil eksik)."
            )
            result["ambiguity_reason"] = "profile_empty"
            return result

        # Reuse extracted fields subject and request if available to strengthen signal
        ext_subject = ""
        ext_request = ""
        if extracted_fields:
            if "subject" in extracted_fields and isinstance(extracted_fields["subject"], dict):
                ext_subject = extracted_fields["subject"].get("value") or ""
            elif "subject" in extracted_fields and isinstance(extracted_fields["subject"], str):
                ext_subject = extracted_fields["subject"]
                
            if "request" in extracted_fields and isinstance(extracted_fields["request"], dict):
                ext_request = extracted_fields["request"].get("value") or ""
            elif "request" in extracted_fields and isinstance(extracted_fields["request"], str):
                ext_request = extracted_fields["request"]

        # Combined search text
        search_text = f"{subject or ''} {request_text or ''} {ext_subject} {ext_request}"
        norm_text = normalize_turkish_text(search_text)

        unit_scores = []

        for unit in units:
            score = 0
            breakdown = {
                "intent_score": 0,
                "keyword_score": 0,
                "doc_type_score": 0,
                "details": []
            }

            # 1. Document Type eşleşmesi (En güçlü yeni sinyal)
            if document_type and document_type in self._doc_type_mapping:
                if unit["unit_id"] in self._doc_type_mapping[document_type]:
                    score += 30
                    breakdown["doc_type_score"] += 30
                    breakdown["details"].append(
                        {
                            "signal": "doc_type_match",
                            "value": 30,
                            "evidence": document_type,
                        }
                    )

            # 2. Intent eşleşmesi
            if process_intent and process_intent in unit.get(
                "supported_intents", []
            ):
                score += 20
                breakdown["intent_score"] += 20
                breakdown["details"].append(
                    {
                        "signal": "intent_match",
                        "value": 20,
                        "evidence": process_intent,
                    }
                )

            # 3. Anahtar kelime eşleşmesi (norm metinde kelime sınırı)
            matched_keywords = []
            for kw in unit.get("keywords", []):
                norm_kw = normalize_turkish_text(kw)
                if not norm_kw:
                    continue
                # Sonekleri yakalamak için kelime sonuna [a-zçğıöşü]* ekliyoruz
                pattern = r"\b" + re.escape(norm_kw) + r"[a-zçğıöşü]*\b"
                if re.search(pattern, norm_text):
                    matched_keywords.append(kw)
                    score += 50
                    breakdown["keyword_score"] += 50
                    breakdown["details"].append(
                        {
                            "signal": "keyword_match",
                            "value": 50,
                            "evidence": kw,
                        }
                    )

            unit_scores.append(
                {
                    "unit": unit,
                    "score": score,
                    "breakdown": breakdown,
                    "matched_keywords": matched_keywords,
                }
            )

        # Skora göre sırala (yüksek → düşük)
        unit_scores.sort(key=lambda x: x["score"], reverse=True)

        best = unit_scores[0] if unit_scores else None
        best_score = best["score"] if best else 0

        # Minimum eşiği 30'a çektik (en az bir process_intent veya doc_type match gerekli)
        if best and best_score >= 30:
            # Top-3 ranked_units hesapla
            for u in unit_scores[:3]:
                result["ranked_units"].append(
                    {
                        "unit_id": u["unit"].get("unit_id", ""),
                        "name": u["unit"]["name"],
                        "score": u["score"],
                    }
                )
                if u["unit"]["name"] != best["unit"]["name"]:
                    result["alternative_units"].append(u["unit"]["name"])

            # Belirsizlik tespiti
            margin = 0
            ambiguous = False
            if len(unit_scores) > 1:
                runner_up = unit_scores[1]["score"]
                margin = best_score - runner_up
                if margin < 15 and best_score < 80:
                    ambiguous = True
                elif margin == 0:
                    ambiguous = True
                    result["ambiguity_reason"] = "low_margin"

            # Ambiguous (Belirsiz) durumda fallback: Yanlış birim atamak yerine None dön (human review)
            if ambiguous or best_score < 40:
                result["needs_human_review"] = True
                result["recommended_unit"] = None
                result["routing_score"] = 0
                result["warnings"].append(
                    "Yönlendirme skoru düşük veya birimler arası fark çok az. "
                    "Yanlış birim atamamak için manuel inceleme önerilir."
                )
                result["routing_confidence_type"] = "rule_margin"
                result["reason"] = "Birden fazla birim eşit derecede olası veya yeterli kanıt yok."
            else:
                result["recommended_unit"] = best["unit"]["name"]
                result["routing_score"] = best_score
                result["score_breakdown"] = best["breakdown"]

                intent_display = (
                    process_intent.replace("_", " ")
                    if process_intent
                    else "belirtilmeyen"
                )
                result["reason"] = (
                    f"Belge '{intent_display}' işlemi veya tipi içerdiği için "
                    f"'{best['unit']['name']}' birimine yönlendirilmesi "
                    f"önerilmektedir."
                )

                if process_intent:
                    result["evidence"].append(f"İşlem Türü: {process_intent}")
                if document_type:
                    result["evidence"].append(f"Evrak Türü: {document_type}")
                if best["matched_keywords"]:
                    result["evidence"].append(
                        f"Eşleşen Kelimeler: {', '.join(best['matched_keywords'])}"
                    )

        else:
            result["needs_human_review"] = True
            result["recommended_unit"] = None
            result["ambiguity_reason"] = "no_strong_match"
            result["reason"] = (
                "Belgenin yönlendirileceği uygun birim güvenilir şekilde "
                "belirlenemedi."
            )

        return result
