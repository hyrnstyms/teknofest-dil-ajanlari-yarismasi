import pytest
from backend.app.agents.routing_agent import RoutingAgent

@pytest.fixture
def agent():
    return RoutingAgent()

def test_routing_bilgi_talebi(agent):
    res = agent.route("dilekce", "bilgi_talebi", "Konu: Bilgi Talebi", "bilgi edinmek istiyorum", {})
    assert res["recommended_unit"] == "Bilgi Edinme Birimi"
    assert res["needs_human_review"] is False
    assert "bilgi talebi işlemi içerdiği için Bilgi Edinme Birimi birimine yönlendirilmesi" in res["reason"]
    assert len(res["score_breakdown"]) > 0

def test_routing_unknown_intent(agent):
    res = agent.route("dilekce", "bilinmeyen_islem", "alakasız", "alakasız", {})
    assert res["recommended_unit"] is None
    assert res["needs_human_review"] is True
    assert "güvenilir şekilde belirlenemedi" in res["reason"]
    assert res["ambiguity_reason"] == "no_strong_match"

def test_routing_empty_registry(monkeypatch):
    agent = RoutingAgent()
    agent.registry = {"units": []}
    res = agent.route("dilekce", "bilgi_talebi", "", "", {})
    assert res["recommended_unit"] is None
    assert res["needs_human_review"] is True
    assert "boş" in res["warnings"][0]
    assert res["ambiguity_reason"] == "registry_empty"

def test_routing_keyword_match(agent):
    res = agent.route("dilekce", "", "Transkript Talebi", "Transkriptimi almak istiyorum", {})
    assert res["recommended_unit"] == "Öğrenci İşleri"
    assert len(res["score_breakdown"]) > 0

def test_routing_ambiguity(agent):
    # Intent empty, but keyword matches both "Öğrenci İşleri" and "Bilgi Edinme Birimi"
    # Actually wait, let's create a fake registry for ambiguity
    agent.registry = {
        "units": [
            {"name": "Birim A", "keywords": ["test", "elma"]},
            {"name": "Birim B", "keywords": ["test", "armut"]}
        ]
    }
    res = agent.route("dilekce", "", "test", "test", {})
    assert res["needs_human_review"] is True
    assert res["ambiguity_reason"] == "low_margin"
    assert res["routing_confidence_type"] == "rule_margin"

def test_routing_alternative_units(agent):
    res = agent.route("dilekce", "bilgi_talebi", "Transkript Talebi", "Transkriptimi almak istiyorum", {})
    # Intent gives 50 points to Bilgi Edinme
    # Keyword gives 20 points to Öğrenci İşleri
    assert res["recommended_unit"] == "Bilgi Edinme Birimi"
    assert "Öğrenci İşleri" in res["alternative_units"]
    assert len(res["ranked_units"]) >= 2
    assert res["ranked_units"][0]["name"] == "Bilgi Edinme Birimi"
    assert res["ranked_units"][1]["name"] == "Öğrenci İşleri"

