from typing import Any, Dict, List
import re
from backend.app.evaluation.schemas import GoldDocument, PredictedDocument
from backend.app.institutions.profile_loader import load_institution_profile

def normalize_turkish_label(text: str) -> str:
    if not text:
        return ""
    trans = str.maketrans("IİÖÜÇĞŞıöüçğş", "iioucgsioucgs")
    t = text.translate(trans).lower()
    t = re.sub(r'[^a-z0-9_]', '', t)
    return t

def normalize_document_type(doc_type: str) -> str:
    if not doc_type:
        return ""
    t = doc_type.lower()
    if "sosyal_yardim_basvuru" in t or "ihale_itirazi" in t or "bilgi_edinme" in t or "tapu_kadastro_basvuru" in t:
        return "dilekce"
    if "kurumlar_arasi_yazi" in t:
        return "resmi_yazi"
    return t

def get_routing_unit_map(institution: str = "kaymakamlik") -> Dict[str, str]:
    profile = load_institution_profile(institution)
    unit_map = {}
    if not profile or not profile.raw.get("birimler"):
        return unit_map
        
    for unit in profile.raw.get("birimler", []):
        unit_id = unit.get("id", "")
        if not unit_id:
            continue
            
        unit_map[unit_id] = unit_id
        
        ad = unit.get("ad", "")
        if ad:
            unit_map[ad] = unit_id
            norm_ad = normalize_turkish_label(ad.replace(" ", "_"))
            unit_map[norm_ad] = unit_id
            
        # Optional: Map keywords or aliases if present
        for alias in unit.get("aliases", []):
            unit_map[alias] = unit_id
            unit_map[normalize_turkish_label(alias.replace(" ", "_"))] = unit_id
            
    return unit_map

def normalize_routing_unit(name: str, unit_map: Dict[str, str]) -> str:
    if not name:
        return ""
    if name in unit_map:
        return unit_map[name]
    norm_name = normalize_turkish_label(name.replace(" ", "_"))
    if norm_name in unit_map:
        return unit_map[norm_name]
    return name

def map_gold_document(doc_dict: Dict[str, Any]) -> GoldDocument:
    return GoldDocument(**doc_dict)
    
def has_missing_fields(missing_fields_dict: Dict[str, Any]) -> bool:
    if not missing_fields_dict:
        return False
    fields = missing_fields_dict.get("missing_fields")
    if isinstance(fields, list):
        return len(fields) > 0
    return False

def normalize_field_value(value: Any, field_type: str = "") -> str:
    if value is None:
        return ""
    val_str = str(value)
    
    # Strip and reduce multiple whitespaces
    val_str = re.sub(r'\s+', ' ', val_str).strip()
    
    if not val_str:
        return ""
        
    # Case-insensitive (Turkish safe lowercase)
    trans = str.maketrans("IİÖÜÇĞŞıöüçğş", "iioucgsioucgs")
    val_str = val_str.translate(trans).lower()
    
    # Date normalization
    if field_type == "tarih" or "date" in field_type:
        # yyyy-mm-dd -> dd.mm.yyyy
        val_str = re.sub(r'^(\d{4})-(\d{2})-(\d{2})$', r'\3.\2.\1', val_str)
        # dd/mm/yyyy -> dd.mm.yyyy
        val_str = re.sub(r'^(\d{2})/(\d{2})/(\d{4})$', r'\1.\2.\3', val_str)
        
    return val_str

def normalize_extracted_fields(agent_fields: Dict[str, Any]) -> Dict[str, Any]:
    mapping = {
        "person_name": "gonderen_adi",
        "document_date": "tarih",
        "subject": "konu",
        "request": "talep_metni",
        "document_number": "referans_no"
    }
    
    normalized = {}
    for agent_key, agent_val_dict in agent_fields.items():
        if agent_key in mapping:
            gold_key = mapping[agent_key]
            # Handle nested dict output like {"value": "...", "evidence": "..."}
            if isinstance(agent_val_dict, dict) and "value" in agent_val_dict:
                val = str(agent_val_dict.get("value", ""))
            else:
                val = str(agent_val_dict)
            
            # The adapter should just map the keys and pass the raw extracted strings.
            # Value normalization for evaluation (like lowercasing/dates) should be done during metric calculation.
            # But we can do basic extraction value unwrapping here.
            normalized[gold_key] = val
    return normalized

def map_predicted_document(doc_id: str, workflow_result: Dict[str, Any]) -> PredictedDocument:
    doc_type = workflow_result.get("document", {}).get("document_type")
    
    routing = workflow_result.get("routing", {})
    recommended_unit = routing.get("recommended_unit")
    if recommended_unit and isinstance(recommended_unit, dict):
        recommended_unit = recommended_unit.get("name", "") or recommended_unit.get("id", "")
    elif not recommended_unit:
        recommended_unit = ""

    ranked_units = [u.get("name") or u.get("id", "") for u in routing.get("ranked_units", []) if isinstance(u, dict)]
    
    missing_fields_data = workflow_result.get("missing_fields", {})
    eksik_alan_var_mi = has_missing_fields(missing_fields_data)
    
    extraction = workflow_result.get("extraction", {})
    extracted_fields = normalize_extracted_fields(extraction.get("fields", {}))
    
    return PredictedDocument(
        id=doc_id,
        evrak_turu=doc_type,
        hedef_birim=recommended_unit,
        ranked_units=ranked_units,
        eksik_alan_var_mi=eksik_alan_var_mi,
        extracted_fields=extracted_fields
    )
