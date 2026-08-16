import pytest
from backend.app.agents.routing_agent import RoutingAgent

@pytest.fixture
def agent():
    return RoutingAgent()

def test_routing_bilgi_talebi(agent):
    res = agent.route("dilekce", "bilgi_talebi", "Konu: Bilgi Talebi", "bilgi edinmek istiyorum", {})
    assert res["recommended_unit"] == "Bilgi Edinme Birimi"
    assert res["needs_human_review"] is False
    assert "bilgi talebi" in res["reason"].lower()

def test_routing_unknown_intent(agent):
    res = agent.route("dilekce", "bilinmeyen_islem", "alakasız", "alakasız", {})
    assert res["recommended_unit"] is None
    assert res["needs_human_review"] is True
    assert "güvenilir şekilde belirlenemedi" in res["reason"]

def test_routing_empty_registry(monkeypatch):
    agent = RoutingAgent()
    agent.registry = {"units": []}
    res = agent.route("dilekce", "bilgi_talebi", "", "", {})
    assert res["recommended_unit"] is None
    assert res["needs_human_review"] is True
    assert "boş" in res["warnings"][0]

def test_routing_keyword_match(agent):
    res = agent.route("dilekce", "", "Transkript Talebi", "Transkriptimi almak istiyorum", {})
    assert res["recommended_unit"] == "Öğrenci İşleri"
