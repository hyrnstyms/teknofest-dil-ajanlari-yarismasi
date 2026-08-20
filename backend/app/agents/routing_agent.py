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


def _load_units_from_profile(institution: str) -> list[dict]:
    """
    InstitutionProfile YAML'dan RoutingAgent'ın kullandığı
    unit listesine dönüştürür.

    Her birimin 'keywords' ve 'supported_intents' alanlarını kullanır.
    """
    try:
        profile: InstitutionProfile = load_institution_profile(institution)
    except (FileNotFoundError, ValueError):
        return []

    units = []
    for birim in profile.birimler:
        if not isinstance(birim, dict):
            continue
        units.append({
            "unit_id": birim.get("id", ""),
            "name": birim.get("ad", ""),
            "keywords": birim.get("anahtar_kelimeler", []),
            # YAML'da supported_intents yoksa evrak_turleri'nden çıkar
            "supported_intents": birim.get("supported_intents", []),
        })
    return units


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
        self._units = _load_units_from_profile(institution)
        self._profile_source = (
            f"data/institutions/{institution}/kurum_profili_{institution}.yaml"
        )

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

        search_text = f"{subject or ''} {request_text or ''}"
        norm_text = normalize_turkish_text(search_text)

        unit_scores = []

        for unit in units:
            score = 0
            breakdown = {
                "intent_score": 0,
                "keyword_score": 0,
                "details": []
            }

            # 1. Intent eşleşmesi (en güçlü sinyal)
            if process_intent and process_intent in unit.get(
                "supported_intents", []
            ):
                score += 50
                breakdown["intent_score"] += 50
                breakdown["details"].append(
                    {
                        "signal": "intent_match",
                        "value": 50,
                        "evidence": process_intent,
                    }
                )

            # 2. Anahtar kelime eşleşmesi (norm metinde kelime sınırı)
            matched_keywords = []
            for kw in unit.get("keywords", []):
                norm_kw = normalize_turkish_text(kw)
                if not norm_kw:
                    continue
                pattern = r"\b" + re.escape(norm_kw) + r"\b"
                if re.search(pattern, norm_text):
                    matched_keywords.append(kw)
                    score += 20
                    breakdown["keyword_score"] += 20
                    breakdown["details"].append(
                        {
                            "signal": "keyword_match",
                            "value": 20,
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

        if best and best_score >= 20:
            result["recommended_unit"] = best["unit"]["name"]
            result["routing_score"] = best_score
            result["score_breakdown"] = best["breakdown"]

            # Top-3 ranked_units
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
                if margin < 10 and best_score < 60:
                    ambiguous = True
                    result["ambiguity_reason"] = "low_margin"

            if ambiguous or best_score < 30:
                result["needs_human_review"] = True
                result["warnings"].append(
                    "Yönlendirme skoru düşük veya birimler arası fark az. "
                    "Manuel inceleme önerilir."
                )
                result["routing_confidence_type"] = "rule_margin"

            # Gerekçe
            intent_display = (
                process_intent.replace("_", " ")
                if process_intent
                else "belirtilmeyen"
            )
            result["reason"] = (
                f"Belge '{intent_display}' işlemi içerdiği için "
                f"'{best['unit']['name']}' birimine yönlendirilmesi "
                f"önerilmektedir."
            )

            # Kanıt listesi
            if process_intent:
                result["evidence"].append(f"İşlem Türü: {process_intent}")
            if best["matched_keywords"]:
                result["evidence"].append(
                    f"Eşleşen Kelimeler: {', '.join(best['matched_keywords'])}"
                )

        else:
            result["needs_human_review"] = True
            result["ambiguity_reason"] = "no_strong_match"
            result["reason"] = (
                "Belgenin yönlendirileceği uygun birim güvenilir şekilde "
                "belirlenemedi."
            )

        return result
