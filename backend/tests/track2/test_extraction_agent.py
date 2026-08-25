from backend.app.agents.extraction_agent import ExtractionAgent

def run_tests():
    print("--- EXTRACTION AGENT REGRESSION TESTS ---")
    agent = ExtractionAgent(llm=None)
    
    # Test A: Ad Soyad Marker
    resA = agent._extract_person_name("Ad Soyad: Mehmet Kaya")
    assert resA[0] == "Mehmet Kaya", f"Test A Failed: {resA}"
    
    # Test B: Separate Ad and Soyad
    textB = "Ad: Mehmet\nSoyad: Kaya"
    resB = agent._extract_person_name(textB)
    assert resB[0] == "Mehmet Kaya", f"Test B Failed: {resB}"
    
    # Test C: Document Number Correct
    resC = agent._extract_document_number("Sayı: E-12345678-105.01-456789")
    assert resC[0] == "E-12345678-105.01-456789", f"Test C Failed: {resC}"
    
    # Test D: Phone number as document number
    resD = agent._extract_document_number("Sayı: 0532 123 45 67")
    assert resD[0] is None, f"Test D Failed: {resD}"
    
    # Test E: Law number
    resE = agent._extract_document_number("4982 sayılı Kanun")
    assert resE[0] is None, f"Test E Failed: {resE}"
    
    # Test F: Subject correct
    resF = agent._extract_subject("Konu: Bilgi Edinme Başvurusu")
    assert resF[0] == "Bilgi Edinme Başvurusu", f"Test F Failed: {resF}"
    
    # Test G: Subject avoid recipient
    resG = agent._extract_subject("Konu: Kaymakamlık Makamına")
    assert resG[0] is None, f"Test G Failed: {resG}"
    
    # Test H: Request correct
    resH = agent._extract_request("Bilgi ve belgelerin tarafıma verilmesini arz ederim.")
    assert "arz ederim" in resH[0], f"Test H Failed: {resH}"
    
    # Test I & J: Context reuse without LLM fallback
    resContext = agent.extract(
        text="Örnek metin.", 
        document_context={"subject_excerpt": "Test Subject", "request_excerpt": "Test Request"}
    )
    assert resContext["fields"]["subject"]["value"] == "Test Subject", "Test I Failed"
    assert resContext["fields"]["subject"]["source"] == "document", "Test I Failed (Source)"
    
    assert resContext["fields"]["request"]["value"] == "Test Request", "Test J Failed"
    assert resContext["fields"]["request"]["source"] == "document", "Test J Failed (Source)"
    
    print("All Regression Tests Passed!")

if __name__ == "__main__":
    run_tests()
