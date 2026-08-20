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
    if not profile or "birimler" not in profile:
        return unit_map
        
    for unit in profile["birimler"]:
        unit_id = unit["id"]
        unit_map[unit_id] = unit_id
        unit_map[unit["ad"]] = unit_id
        norm_ad = normalize_turkish_label(unit["ad"].replace(" ", "_"))
        unit_map[norm_ad] = unit_id
        
        name_lower = unit["ad"].lower()
        if "yazı işleri" in name_lower or "yazi isleri" in name_lower:
            unit_map["yazi_isleri"] = unit_id
        elif "nüfus" in name_lower or "nufus" in name_lower:
            unit_map["nufus"] = unit_id
        elif "sosyal" in name_lower or "sydv" in name_lower:
            unit_map["sydv"] = unit_id
            
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
    
def map_predicted_document(doc_id: str, workflow_result: Dict[str, Any]) -> PredictedDocument:
    doc_type = workflow_result.get("document_agent", {}).get("document_type")
    
    routing = workflow_result.get("routing_agent", {})
    recommended_unit = routing.get("recommended_unit")
    if recommended_unit and isinstance(recommended_unit, dict):
        recommended_unit = recommended_unit.get("name", "")
    elif not recommended_unit:
        recommended_unit = ""

    ranked_units = [u.get("name") for u in routing.get("ranked_units", [])]
    
    missing_fields = workflow_result.get("missing_field_agent", {})
    eksik_alan_var_mi = missing_fields.get("needs_human_review", None)
    
    extraction = workflow_result.get("extraction_agent", {})
    extracted_fields = extraction.get("fields", {})
    
    return PredictedDocument(
        id=doc_id,
        evrak_turu=doc_type,
        hedef_birim=recommended_unit,
        ranked_units=ranked_units,
        eksik_alan_var_mi=eksik_alan_var_mi,
        extracted_fields=extracted_fields
    )
