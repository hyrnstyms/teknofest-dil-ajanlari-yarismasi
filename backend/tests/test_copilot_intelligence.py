import pytest
from backend.app.agents.chat_agent import resolve_chat_mode, handle_chat_message

def test_handle_workflow_action():
    # Write mode (W)
    context = {"user_context": {"role": "EVRAK_KAYIT"}}
    response = handle_chat_message("Fen işlerine gönder", workflow_context=context, resolved_mode="workflow_action")
    
    assert isinstance(response, dict)
    assert response["mode"] == "workflow_action"
    assert "pending_action" in response
    
    action = response["pending_action"]
    assert action["type"] == "route_case"
    assert action["confirmation_required"] is True

def test_handle_clarification_action():
    # Write mode (R)
    context = {"user_context": {"role": "BIRIM_PERSONELI"}}
    response = handle_chat_message("Vatandaştan ek bilgi iste", workflow_context=context, resolved_mode="clarification_action")
    
    assert isinstance(response, dict)
    assert response["mode"] == "clarification_action"
    assert "pending_action" in response
    
    action = response["pending_action"]
    assert action["type"] == "request_clarification"
    assert action["confirmation_required"] is True

def test_handle_case_query_state():
    # Read mode (C)
    context = {"user_context": {"role": "EVRAK_KAYIT"}, "analysis_state": {"status": "WAITING_APPROVAL"}}
    response = handle_chat_message("Dosya ne durumda?", workflow_context=context, resolved_mode="case_query_state")
    
    # Should not be a dict with pending_action, just a string
    assert isinstance(response, str)
    assert "WAITING_APPROVAL" in response

def test_handle_inbox_query():
    # Read mode (I)
    context = {"user_context": {"role": "EVRAK_KAYIT"}}
    response = handle_chat_message("Üzerimde kaç iş var?", workflow_context=context, resolved_mode="inbox_query")
    
    assert isinstance(response, str)
    assert "gelen kutunuzda" in response

def test_permission_evrak_kayit_draft_edit_denied():
    context = {"user_context": {"role": "EVRAK_KAYIT", "department": "Yazı İşleri"}}
    response = handle_chat_message("Taslağı düzenle", workflow_context=context, resolved_mode="taslak_duzenleme", current_draft={"text": "Taslak"})
    
    assert isinstance(response, str)
    assert "Yetki Hatası" in response
    assert "Evrak Kayıt" in response

def test_permission_birim_personeli_wrong_department_denied():
    context = {
        "user_context": {"role": "BIRIM_PERSONELI", "department": "Fen İşleri"},
        "analysis_state": {"department": "İmar"}
    }
    response = handle_chat_message("Taslağı düzenle", workflow_context=context, resolved_mode="taslak_duzenleme", current_draft={"text": "Taslak"})
    
    assert isinstance(response, str)
    assert "Yetki Hatası" in response
    assert "kendi biriminizdeki" in response

def test_permission_birim_personeli_correct_department_allowed():
    context = {
        "user_context": {"role": "BIRIM_PERSONELI", "department": "Fen İşleri"},
        "analysis_state": {"department": "Fen İşleri"}
    }
    # It should pass permission check and return dict (or reject because of missing draft context, but we provide mock draft)
    response = handle_chat_message("Taslağı düzenle", workflow_context=context, resolved_mode="taslak_duzenleme", current_draft={"text": "Taslak"})
    
    # Should hit draft logic which might fail if draft string is not updated via LLM, but for this test we only check it didn't return permission denied
    assert isinstance(response, dict) or "Yetki Hatası" not in response

def test_stream_copilot_deadline_edge_case(monkeypatch):
    from backend.app.agents.chat_agent import stream_copilot_response
    import backend.app.agents.chat_agent as chat_agent
    import unittest.mock as mock

    def mock_build_rag(*args, **kwargs):
        return [{
            "law_number": "3071",
            "title": "Dilekçe Hakkının Kullanılmasına Dair Kanun",
            "madde_no": "4",
            "excerpt": "Başvurular en geç otuz gün içinde cevaplandırılır.",
            "score": 0.9,
        }]

    monkeypatch.setattr(chat_agent, "_build_rag_sources", mock_build_rag)
    
    # Simulate mevzuat with 'kaç gün' but no received_at
    with mock.patch("backend.app.agents.chat_agent.resolve_chat_mode", return_value="mevzuat"):
        stream = stream_copilot_response(
            message="Mevzuata göre kaç gün sürem var?",
            history=[],
            analysis_state={"id": "doc1"}, # No received_at
            institution_id=None,
            user_context={"role": "EVRAK_KAYIT"}
        )
        
        # Read the stream chunks
        chunks = list(stream)
    
    # Since it's a generator yielding strings, we join and check
    full_output = "".join(chunks)
    assert "güvenilir alınma tarihi gerekli" in full_output
    assert "event: sources" not in full_output

def test_handle_inbox_query_adapter():
    context = {"user_context": {"role": "EVRAK_KAYIT", "department": "Yazı İşleri"}}
    response = handle_chat_message("Gelen kutumda ne var?", workflow_context=context, resolved_mode="inbox_query")
    
    assert isinstance(response, str)
    assert "Yazı İşleri" in response
    assert "EVRAK_KAYIT" in response

