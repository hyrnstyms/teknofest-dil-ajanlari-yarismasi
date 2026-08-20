import pytest
from pydantic import ValidationError
from backend.app.graph.state import DocumentState

def test_document_state_new_fields():
    # muhatap, muhatap_turu, karar_kaynagi should be accepted
    state = DocumentState(
        document_id="test-1",
        raw_text="Merhaba",
        muhatap={"tur": "kurum", "isim": "Valilik"},
        muhatap_turu="kurum_ust",
        karar_kaynagi="kural_tabanli"
    )
    assert state.muhatap == {"tur": "kurum", "isim": "Valilik"}
    assert state.muhatap_turu == "kurum_ust"
    assert state.karar_kaynagi == "kural_tabanli"
    assert state.kurum_profili_id == "kaymakamlik_v1"

def test_document_state_validation():
    # Valid scores should not raise errors
    state = DocumentState(
        confidence=0.5,
        document_confidence=0.0,
        routing_confidence=1.0,
        quality_score=0.9
    )
    assert state.confidence == 0.5
    
    # Invalid scores should raise ValidationError
    with pytest.raises(ValidationError):
        DocumentState(confidence=1.5)
        
    with pytest.raises(ValidationError):
        DocumentState(document_confidence=-0.1)

    with pytest.raises(ValidationError):
        DocumentState(routing_confidence=1.01)

    with pytest.raises(ValidationError):
        DocumentState(quality_score=-5.0)

def test_muhatap_turu_enum_validation():
    with pytest.raises(ValidationError):
        DocumentState(muhatap_turu="gecersiz_tur")
        
def test_karar_kaynagi_enum_validation():
    with pytest.raises(ValidationError):
        DocumentState(karar_kaynagi="gecersiz_kaynak")
