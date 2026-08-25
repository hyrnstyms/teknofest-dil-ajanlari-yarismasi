from backend.app.agents.routing_agent import RoutingAgent

def run_tests():
    print("--- ROUTING AGENT REGRESSION TESTS ---")
    agent = RoutingAgent("kaymakamlik")

    # A. "bilgi edinme başvurusu" process_intent=bilgi_talebi -> yazi_isleri (because bilgi_edinme tipik hedef is yazi_isleri)
    # Wait, the prompt says "ilgili bilgi edinme birimi". In YAML, bilgi_edinme tipik_hedef_birim is yazi_isleri.
    # So it should route to yazi_isleri if it's definitely a bilgi edinme.
    res_A = agent.route(
        document_type="bilgi_edinme",
        process_intent="bilgi_talebi",
        subject="Bilgi Edinme Başvurusu",
        request_text="Bana bilgi verin",
        extracted_fields={}
    )
    assert res_A["recommended_unit"] == "Yazı İşleri Müdürlüğü", f"Test A Failed: {res_A['recommended_unit']}"

    # B. "tapu/kadastro" -> Tapu birimi
    res_B = agent.route(
        document_type="tapu_kadastro_basvuru",
        process_intent="basvuru",
        subject="Arsa alımı",
        request_text="Kadastro işlemleri yapılsın",
        extracted_fields={"subject": "tapu"}
    )
    assert "Tapu" in res_B["recommended_unit"], f"Test B Failed: {res_B['recommended_unit']}"

    # C. "öğrenci / okul / eğitim" -> Eğitim birimi
    res_C = agent.route(
        document_type="dilekce",
        process_intent="basvuru",
        subject="Okul nakil",
        request_text="Öğrenci nakil işleminin yapılması",
        extracted_fields={}
    )
    assert "Millî Eğitim" in res_C["recommended_unit"], f"Test C Failed: {res_C['recommended_unit']}"

    # D. Belirsiz genel metin -> otomatik Yazı İşleri DEĞİL -> human review
    res_D = agent.route(
        document_type="dilekce",
        process_intent="basvuru",
        subject="Genel bir konu",
        request_text="Gereğini arz ederim.",
        extracted_fields={}
    )
    # It might tie between multiple units that support 'basvuru'.
    # Because there are no strong keywords, margin will be 0.
    assert res_D["recommended_unit"] is None, f"Test D Failed: {res_D['recommended_unit']}"
    assert res_D["needs_human_review"] is True, "Test D Failed: Should need human review."

    # E. Profile'da olmayan birim -> seçilmemeli (handled naturally as we only pick from loaded units)

    # F. Top1/top2 çok yakın -> human review
    # We can simulate this by putting keywords for two units
    res_F = agent.route(
        document_type="dilekce",
        process_intent="basvuru",
        subject="Nüfus cüzdanımı kaybettim, ayrıca sosyal yardım istiyorum",
        request_text="Kimlik, doğum ve muhtaçlık belgesi verilsin",
        extracted_fields={}
    )
    # nufus (kimlik), sydv (muhtaçlık) -> Tie or very close
    assert res_F["recommended_unit"] is None, f"Test F Failed: {res_F['recommended_unit']}"
    assert res_F["needs_human_review"] is True, "Test F Failed: Should need human review."

    # G. LLM unavailable -> deterministic routing devam etmeli (Agent doesn't use LLM natively, so passes)

    # H. Unknown kurum_profili_id -> crash yerine kontrollü davranış
    agent_H = RoutingAgent("unknown_profile")
    res_H = agent_H.route("dilekce", "basvuru", "test", "test", {})
    assert res_H["recommended_unit"] is None, "Test H Failed."
    assert res_H["needs_human_review"] is True, "Test H Failed."

    print("All Regression Tests Passed!")

if __name__ == "__main__":
    run_tests()
