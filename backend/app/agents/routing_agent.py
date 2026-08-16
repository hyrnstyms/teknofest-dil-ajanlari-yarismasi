import json
import os
from typing import Dict, Any, List

class RoutingAgent:
    def __init__(self, registry_path: str = None):
        if not registry_path:
            # Default to the data/routing/unit_registry.json
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
            "reason": None,
            "evidence": [],
            "routing_score": 0.0,
            "score_type": "rule_match",
            "registry_source": self.registry.get("registry_type", "unknown"),
            "needs_human_review": False,
            "warnings": []
        }
        
        units = self.registry.get("units", [])
        if not units:
            result["needs_human_review"] = True
            result["warnings"].append("Birim kayıt (registry) dosyası bulunamadı veya boş.")
            result["reason"] = "Belgenin yönlendirileceği uygun birim güvenilir şekilde belirlenemedi."
            return result

        best_match = None
        best_score = 0
        
        # Simple deterministic scoring
        search_text = f"{subject} {request_text}".lower()
        
        for unit in units:
            score = 0
            
            # 1. Intent matching (Strongest)
            if process_intent and process_intent in unit.get("supported_intents", []):
                score += 50
                
            # 2. Keyword matching in subject/request
            keywords = unit.get("keywords", [])
            for kw in keywords:
                if kw.lower() in search_text:
                    score += 20
                    
            if score > best_score:
                best_score = score
                best_match = unit

        if best_match and best_score >= 20:
            result["recommended_unit"] = best_match["name"]
            result["routing_score"] = best_score
            
            # Create a Turkish reason
            intent_display = process_intent.replace("_", " ") if process_intent else "belirtilmeyen"
            result["reason"] = f"Belge {intent_display} işlemi içerdiği için {best_match['name']}ine yönlendirilmesi önerilmektedir."
            
            # Evidence
            if process_intent:
                result["evidence"].append(f"İşlem Türü: {process_intent}")
            if request_text:
                result["evidence"].append(f"Talep: {request_text[:100]}...")
                
        else:
            result["needs_human_review"] = True
            result["reason"] = "Belgenin yönlendirileceği uygun birim güvenilir şekilde belirlenemedi."
            
        return result
