import json
import os
import re
from typing import Dict, Any, List

def normalize_turkish_text(text: str) -> str:
    if not text:
        return ""
    # Basit Türkçe harf dönüşümü
    trans = str.maketrans("IİÖÜÇĞ", "ıiöüçğ")
    text = text.translate(trans).lower()
    # Noktalama işaretlerini boşlukla değiştir
    text = re.sub(r'[^\w\s]', ' ', text)
    # Fazla boşlukları temizle
    return re.sub(r'\s+', ' ', text).strip()

class RoutingAgent:
    def __init__(self, registry_path: str = None):
        if not registry_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            registry_path = os.path.join(base_dir, "data", "routing", "unit_registry.json")
        
        self.registry = {"units": [], "registry_type": "unknown"}
        if os.path.exists(registry_path):
            with open(registry_path, "r", encoding="utf-8") as f:
                self.registry = json.load(f)

    def route(
        self,
        document_type: str,
        process_intent: str,
        subject: str,
        request_text: str,
        extracted_fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        result = {
            "recommended_unit": None,
            "alternative_units": [],
            "ranked_units": [],
            "reason": None,
            "evidence": [],
            "routing_score": 0.0,
            "score_type": "rule_match",
            "score_breakdown": [],
            "registry_source": self.registry.get("registry_type", "unknown"),
            "needs_human_review": False,
            "warnings": []
        }
        
        units = self.registry.get("units", [])
        if not units:
            result["needs_human_review"] = True
            result["warnings"].append("Birim kayıt (registry) dosyası bulunamadı veya boş.")
            result["reason"] = "Belgenin yönlendirileceği uygun birim güvenilir şekilde belirlenemedi."
            result["ambiguity_reason"] = "registry_empty"
            return result

        search_text = f"{subject or ''} {request_text or ''}"
        norm_text = normalize_turkish_text(search_text)
        
        unit_scores = []
        
        for unit in units:
            score = 0
            breakdown = []
            
            # 1. Intent matching (Strongest)
            if process_intent and process_intent in unit.get("supported_intents", []):
                score += 50
                breakdown.append({
                    "signal": "intent_match",
                    "value": 50,
                    "evidence": process_intent
                })
                
            # 2. Keyword matching in normalized subject/request with word boundaries
            keywords = unit.get("keywords", [])
            matched_keywords = []
            for kw in keywords:
                norm_kw = normalize_turkish_text(kw)
                if not norm_kw:
                    continue
                # Kelime sınırlarını kontrol et
                pattern = r'\b' + re.escape(norm_kw) + r'\b'
                if re.search(pattern, norm_text):
                    matched_keywords.append(kw)
                    score += 20
                    breakdown.append({
                        "signal": "keyword_match",
                        "value": 20,
                        "evidence": kw
                    })
            
            unit_scores.append({
                "unit": unit,
                "score": score,
                "breakdown": breakdown,
                "matched_keywords": matched_keywords
            })

        # Sort by score descending
        unit_scores.sort(key=lambda x: x["score"], reverse=True)
        
        best_match = unit_scores[0] if unit_scores else None
        best_score = best_match["score"] if best_match else 0
        
        if best_match and best_score >= 20:
            result["recommended_unit"] = best_match["unit"]["name"]
            result["routing_score"] = best_score
            result["score_breakdown"] = best_match["breakdown"]
            
            # Populate ranked units
            for u in unit_scores[:3]:
                result["ranked_units"].append({
                    "name": u["unit"]["name"],
                    "score": u["score"]
                })
                if u["unit"]["name"] != best_match["unit"]["name"]:
                    result["alternative_units"].append(u["unit"]["name"])
            
            # Check ambiguity
            ambiguous = False
            margin = 0
            if len(unit_scores) > 1:
                runner_up_score = unit_scores[1]["score"]
                margin = best_score - runner_up_score
                if margin < 10 and best_score < 60:
                    ambiguous = True
                    result["ambiguity_reason"] = "low_margin"
            
            if ambiguous or best_score < 30:
                result["needs_human_review"] = True
                result["warnings"].append("Yönlendirme skoru düşük veya birimler arası fark az. Manuel inceleme önerilir.")
                result["routing_confidence_type"] = "rule_margin"
                
            # Create a generic Turkish reason
            intent_display = process_intent.replace("_", " ") if process_intent else "belirtilmeyen"
            result["reason"] = f"Belge {intent_display} işlemi içerdiği için {best_match['unit']['name']} birimine yönlendirilmesi önerilmektedir."
            
            # Evidence
            if process_intent:
                result["evidence"].append(f"İşlem Türü: {process_intent}")
            if best_match["matched_keywords"]:
                result["evidence"].append(f"Eşleşen Kelimeler: {', '.join(best_match['matched_keywords'])}")
                
        else:
            result["needs_human_review"] = True
            result["ambiguity_reason"] = "no_strong_match"
            result["reason"] = "Belgenin yönlendirileceği uygun birim güvenilir şekilde belirlenemedi."
            
        return result
