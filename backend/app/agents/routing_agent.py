import re
from typing import Dict, Any

from backend.app.institutions.profile_loader import (
    load_institution_profile,
    InstitutionProfile,
)

# Yarışma demosunda aktif kurum
_DEFAULT_INSTITUTION = "kaymakamlik"
_GENERIC_KEYWORDS = {"ruhsat", "yardım", "yardim", "itiraz", "şikayet", "sikayet", "başvuru", "basvuru", "talep", "istek", "dilekçe", "dilekce"}
_EXEMPLAR_MIN_SCORE = 0.55
_EXEMPLAR_MIN_GAP = 0.04


def normalize_turkish_text(text: str) -> str:
    if not text:
        return ""
    trans = str.maketrans("IİÖÜÇĞŞ", "ıiöüçğş")
    text = text.translate(trans).lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _has_explicit_target(norm_text: str, unit_name: str) -> bool:
    norm_name = normalize_turkish_text(unit_name)
    aliases = {norm_name}
    if norm_name.startswith("ilçe "):
        aliases.add(norm_name.removeprefix("ilçe "))

    for alias in aliases:
        if not alias:
            continue
        # Yalın birim adı gönderen/antet bilgisi olabilir. Yalnız hedefi veya
        # görevlendirilen birimi gösteren yönelme/eyleyen bağlamını güçlendir.
        suffixed_target = (
            r"\b"
            + re.escape(alias)
            + r"(?:ne|na|nce|nca)\b"
        )
        by_unit = (
            r"\b"
            + re.escape(alias)
            + r"\s+tarafından\b"
        )
        if re.search(suffixed_target, norm_text) or re.search(by_unit, norm_text):
            return True
    return False


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
        retrieved_documents: list[dict[str, Any]] | None = None,
        document_subtype: str = None,
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
                "explicit_target_score": 0,
                "intent_score": 0,
                "keyword_score": 0,
                "doc_type_score": 0,
                "subtype_score": 0,
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

        labelled_exemplars = sorted(
            (
                candidate
                for candidate in (retrieved_documents or [])
                if candidate.get("expected_unit")
            ),
            key=lambda candidate: float(candidate.get("score") or 0.0),
            reverse=True,
        )
        exemplar_unit = None
        exemplar_score = 0.0
        if labelled_exemplars:
            top_exemplar = labelled_exemplars[0]
            exemplar_score = float(top_exemplar.get("score") or 0.0)
            runner_up_score = (
                float(labelled_exemplars[1].get("score") or 0.0)
                if len(labelled_exemplars) > 1
                else 0.0
            )
            if (
                exemplar_score >= _EXEMPLAR_MIN_SCORE
                and exemplar_score - runner_up_score >= _EXEMPLAR_MIN_GAP
            ):
                exemplar_unit = str(top_exemplar["expected_unit"])

        unit_scores = []

        for unit in units:
            score = 0
            breakdown = {
                "explicit_target_score": 0,
                "intent_score": 0,
                "keyword_score": 0,
                "doc_type_score": 0,
                "subtype_score": 0,
                "details": []
            }

            # 1. Açık hedef birim sinyali
            if _has_explicit_target(norm_text, unit["name"]):
                score += 100
                breakdown["explicit_target_score"] += 100
                breakdown["details"].append(
                    {
                        "signal": "explicit_target_match",
                        "value": 100,
                        "evidence": unit["name"],
                    }
                )

            # 2. Document Type / Subtype eşleşmesi
            matched_type = None
            if document_subtype and document_subtype in self._doc_type_mapping:
                matched_type = document_subtype
            elif document_type and document_type in self._doc_type_mapping:
                matched_type = document_type
            
            if matched_type and unit["unit_id"] in self._doc_type_mapping[matched_type]:
                score += 30
                if matched_type == document_subtype:
                    breakdown["subtype_score"] += 30
                    breakdown["details"].append(
                        {
                            "signal": "subtype_match",
                            "value": 30,
                            "evidence": document_subtype,
                        }
                    )
                else:
                    breakdown["doc_type_score"] += 30
                    breakdown["details"].append(
                        {
                            "signal": "doc_type_match",
                            "value": 30,
                            "evidence": document_type,
                        }
                    )

            # 3. Intent eşleşmesi
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

            # 4. Anahtar kelime eşleşmesi (norm metinde kelime sınırı)
            matched_keywords = []
            for kw in unit.get("keywords", []):
                norm_kw = normalize_turkish_text(kw)
                if not norm_kw:
                    continue
                # Sonekleri yakalamak için kelime sonuna [a-zçğıöşü]* ekliyoruz
                pattern = r"\b" + re.escape(norm_kw) + r"[a-zçğıöşü]*\b"
                if re.search(pattern, norm_text):
                    matched_keywords.append(kw)
                    if norm_kw in _GENERIC_KEYWORDS:
                        keyword_value = 20
                    elif " " in norm_kw:
                        keyword_value = 60
                    else:
                        keyword_value = 50
                    score += keyword_value
                    breakdown["keyword_score"] += keyword_value
                    breakdown["details"].append(
                        {
                            "signal": "keyword_match",
                            "value": keyword_value,
                            "evidence": kw,
                        }
                    )

            # High-similarity, labelled synthetic examples are a bounded,
            # explainable signal. They complement but do not replace rules.
            if exemplar_unit and unit["unit_id"] == exemplar_unit:
                score += 35
                breakdown["details"].append(
                    {
                        "signal": "document_exemplar_match",
                        "value": 35,
                        "evidence": f"{exemplar_unit} ({exemplar_score:.3f})",
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
                if margin < 15:
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
                if document_subtype:
                    result["evidence"].append(f"Evrak Alt Türü: {document_subtype}")
                elif document_type:
                    result["evidence"].append(f"Evrak Türü: {document_type}")
                if best["matched_keywords"]:
                    result["evidence"].append(
                        f"Eşleşen Kelimeler: {', '.join(best['matched_keywords'])}"
                    )
                if best["breakdown"]["explicit_target_score"]:
                    result["evidence"].append(
                        f"Açık Hedef Birim: {best['unit']['name']}"
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
