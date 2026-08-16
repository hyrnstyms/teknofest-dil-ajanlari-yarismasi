from typing import Dict, Any

class QualityAgent:
    def __init__(self, registry_path: str = None):
        import os
        import json
        if not registry_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            registry_path = os.path.join(base_dir, "data", "routing", "unit_registry.json")
            
        self.valid_units = set()
        if os.path.exists(registry_path):
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = json.load(f)
                for u in registry.get("units", []):
                    self.valid_units.add(u["name"])

    def check_quality(
        self,
        document: Dict[str, Any],
        extraction: Dict[str, Any],
        legal_analysis: Dict[str, Any],
        missing_fields: Dict[str, Any],
        summary: Dict[str, Any],
        routing: Dict[str, Any],
        draft: Dict[str, Any],
        human_review: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        result = {
            "status": "pass",
            "checks": {},
            "issues": [],
            "warnings": [],
            "requires_human_review": human_review.get("required", False)
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

        # 1. document_classification_present
        if document and document.get("document_type"):
            add_check("document_classification", "pass", "Evrak sınıflandırması mevcut.")
        else:
            add_check("document_classification", "fail", "Evrak sınıflandırması yapılamadı.")

        # 2. extraction_present
        if extraction and extraction.get("fields"):
            add_check("extraction_present", "pass", "Bilgi çıkarımı yapıldı.")
        else:
            add_check("extraction_present", "fail", "Belgeden hiçbir bilgi çıkarılamadı.")

        # 3. missing_field_analysis_present
        if missing_fields:
            if missing_fields.get("needs_human_review"):
                add_check("missing_fields", "warning", "Eksik alan analizi personel incelemesi gerektiriyor.")
            else:
                add_check("missing_fields", "pass", "Eksik alan kontrolü yapıldı.")
        else:
            add_check("missing_fields", "fail", "Eksik alan analizi bulunamadı.")

        # 4. legal_evidence_validated
        if legal_analysis:
            # Assuming legal_analysis has 'evidence' and 'sources'
            sources = legal_analysis.get("sources", [])
            if sources:
                add_check("legal_evidence", "pass", "Mevzuat dayanağı mevcut.")
            else:
                add_check("legal_evidence", "warning", "Doğrulanmış hukuki mevzuat dayanağı bulunamadı.")
        else:
            add_check("legal_evidence", "warning", "Mevzuat analizi mevcut değil.")

        # 5. routing_unit_in_registry
        rec_unit = routing.get("recommended_unit")
        if routing.get("needs_human_review") or not rec_unit:
            add_check("routing", "warning", "Birim yönlendirmesi belirsiz, manuel inceleme gerekiyor.")
        else:
            if rec_unit in self.valid_units:
                add_check("routing", "pass", "Önerilen birim sistem kayıtlarında mevcut.")
            else:
                add_check("routing", "fail", f"Önerilen '{rec_unit}' birimi sistem kayıtlarında (registry) bulunamadı.")

        # 6. draft checks
        if draft:
            if not draft.get("draft_text") and draft.get("draft_type"):
                add_check("draft", "fail", "Taslak metin oluşturulması beklenirken boş döndü.")
            else:
                add_check("draft", "pass", "Resmî yazı taslağı başarıyla oluşturuldu.")
        else:
            add_check("draft", "warning", "Resmî yazı taslağı mevcut değil.")
            
        # 7. human_review checks
        if result["requires_human_review"]:
            add_check("human_review", "warning", "Kritik işlemler veya belirsizlikler nedeniyle personel onayı gerekiyor.")
        
        return result
