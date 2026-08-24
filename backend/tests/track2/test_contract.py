from backend.app.evaluation.adapters import normalize_extracted_fields, normalize_turkish_label, normalize_field_value, normalize_document_type

def run_tests():
    print("--- REGRESSION TESTS ---")
    
    # Test 1: Exact matches
    agent_output = {
        "person_name": {"value": "Ahmet Yılmaz", "evidence": "Ahmet Yılmaz"},
        "document_date": {"value": "12/08/2026", "evidence": "12/08/2026"},
        "subject": {"value": "Şikayet Bildirimi", "evidence": "Şikayet"},
        "request": {"value": "Gereğinin yapılmasını arz ederim.", "evidence": ""},
        "document_number": {"value": "12345", "evidence": ""}
    }
    norm = normalize_extracted_fields(agent_output)
    
    assert norm.get("gonderen_adi") == "Ahmet Yılmaz", "Test 1 Failed"
    assert norm.get("tarih") == "12/08/2026", "Test 1 Failed"
    assert norm.get("konu") == "Şikayet Bildirimi", "Test 1 Failed"
    assert norm.get("talep_metni") == "Gereğinin yapılmasını arz ederim.", "Test 1 Failed"
    assert norm.get("referans_no") == "12345", "Test 1 Failed"
    print("Test 1 (Mapping) Passed")
    
    # Test 2: Unknown keys ignored
    agent_output_2 = {
        "person_name": {"value": "Veli", "evidence": ""},
        "unknown_key": {"value": "Ignore me", "evidence": ""}
    }
    norm_2 = normalize_extracted_fields(agent_output_2)
    assert "gonderen_adi" in norm_2, "Test 2 Failed"
    assert "unknown_key" not in norm_2, "Test 2 Failed"
    print("Test 2 (Unknown keys ignored) Passed")
    
    # Test 3: Missing keys don't crash
    agent_output_3 = {}
    norm_3 = normalize_extracted_fields(agent_output_3)
    assert norm_3 == {}, "Test 3 Failed"
    print("Test 3 (Empty input) Passed")

    # Test 4: Value normalization (Date and string)
    assert normalize_field_value("2026-08-12", "tarih") == "12.08.2026", "Date normalization failed"
    assert normalize_field_value("12/08/2026", "tarih") == "12.08.2026", "Date normalization failed"
    assert normalize_field_value(" MEhmet   KAYA ", "gonderen_adi") == "mehmet kaya", "String normalization failed"
    assert normalize_field_value(None, "konu") == "", "None handling failed"
    print("Test 4 (Value Normalization) Passed")
    
    # Test 5: Document Type Normalization match
    assert normalize_document_type("ihale_itirazi") == "dilekce", "Document type normalization failed"
    assert normalize_document_type("sosyal_yardim_basvuru") == "dilekce", "Document type normalization failed"
    assert normalize_document_type("bilgi_edinme") == "dilekce", "Document type normalization failed"
    assert normalize_document_type("kurumlar_arasi_yazi") == "resmi_yazi", "Document type normalization failed"
    assert normalize_document_type("dilekce") == "dilekce", "Document type normalization failed"
    
    gold_raw = "ihale_itirazi"
    pred_raw = "dilekce"
    
    gold_norm = normalize_document_type(gold_raw)
    pred_norm = normalize_document_type(pred_raw)
    
    raw_match = (gold_raw == pred_raw)
    normalized_match = (gold_norm == pred_norm)
    
    assert raw_match is False, "Raw match should be False"
    assert normalized_match is True, "Normalized match should be True"
    print("Test 5 (Document Type Normalization Match) Passed")

if __name__ == "__main__":
    run_tests()
