import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath('.'))

from backend.app.graph.workflow import KamuaiWorkflow

def main():
    with patch('backend.app.graph.workflow.create_llm_client') as mock_llm_factory, \
         patch('backend.app.agents.legal_agent.LegalAgent.analyze') as mock_legal, \
         patch('backend.app.agents.writing_agent.WritingAgent.draft') as mock_writing, \
         patch('backend.app.agents.document_agent.DocumentAgent.analyze') as mock_doc, \
         patch('backend.app.agents.extraction_agent.ExtractionAgent.extract') as mock_ext, \
         patch('backend.app.agents.summary_agent.SummaryAgent.summarize') as mock_sum, \
         patch('backend.app.agents.routing_agent.RoutingAgent.route') as mock_route, \
         patch('backend.app.agents.missing_field_agent.MissingFieldAgent.check_missing_fields') as mock_missing:

        # Mocks
        mock_doc.return_value = {"document_type": "Dilekçe", "process_intent": "Bilgi Talebi"}
        mock_ext.return_value = {"fields": {"person_name": {"value": "Ahmet Yılmaz"}}}
        mock_legal.return_value = {"evidence": ["Madde 1"], "sources": [{"id": "1", "text": "Kanun"}]}
        mock_missing.return_value = {"missing_fields": [], "needs_human_review": False}
        mock_sum.return_value = {"short_summary": "Ahmet Yılmaz bilgi talep ediyor."}
        mock_route.return_value = {"recommended_unit": "Yazı İşleri", "confidence": 0.9, "needs_human_review": False}
        mock_writing.return_value = {
            "draft_type": "cevap_yazisi", 
            "draft_text": "Cevap metni",
            "official_render": {
                "attempted": True,
                "success": True,
                "template": "cevap_yazisi.jinja2",
                "missing_fields": [],
                "warnings": [],
                "source_map": {},
                "fallback_policies": {},
                "context": {
                    "sayi": "E-123-903.07.02-456",
                    "tarih": "20.08.2026",
                    "konu": "Bilgi Talebi Hk.",
                    "muhatap": {"tur": "gercek_kisi", "isim": "Ahmet Yılmaz"},
                    "ilgi": [{"tarih": "12.08.2026", "sayi": "123", "konu": "dilekçe"}],
                    "tc_baslik": {"idare_adi": "TEST İDARESİ", "birim_adi": "Test Birimi"},
                    "metin_paragraflari": ["Paragraf 1"],
                    "imza": {"ad_soyad": "Ali Yılmaz", "unvan": "Müdür"}
                }
            }
        }

        wf = KamuaiWorkflow()
        
        # Test 1: Normal Evrak (Geçerli Format)
        print("--- Test 1: Normal Evrak (Geçerli Format) ---")
        res = wf.run("Ahmet Yılmaz olarak bilgi talep ediyorum.")
        print("Quality Issues:", res.get("quality", {}).get("issues", []))
        print("Quality Warnings:", res.get("quality", {}).get("warnings", []))
        print("Human Review Status:", res.get("human_review", {}))
        
        # Test 2: Geçersiz Format (Sayı Formatı Bozuk)
        print("\n--- Test 2: Geçersiz Format (Sayı Formatı Bozuk) ---")
        bad_context = dict(mock_writing.return_value["official_render"]["context"])
        bad_context["sayi"] = "YANLIS-SAYI"
        mock_writing.return_value["official_render"]["context"] = bad_context
        res2 = wf.run("Ahmet Yılmaz, hatalı format.")
        print("Quality Issues:", res2.get("quality", {}).get("issues", []))
        print("Human Review Status:", res2.get("human_review", {}))

        # Test 3: Eksik Context (Render failure)
        print("\n--- Test 3: Eksik Context (Render Failure) ---")
        mock_writing.return_value["official_render"] = {"attempted": True, "success": False}
        res3 = wf.run("Render patladı.")
        print("Quality Issues:", res3.get("quality", {}).get("issues", []))
        print("Quality Warnings:", res3.get("quality", {}).get("warnings", []))

if __name__ == '__main__':
    main()
