"""
backend/app/official_writing/context_adapter.py
──────────────────────────────────────────────────────────────────────────────
Writing Agent çıktısını ve State verilerini alıp,
Official Writing Template Motoru için GÜVENLİ bir context oluşturur.

KURALLAR:
1. Asla uydurma veri üretilmez (sayı, tarih, isim, imza vb.).
2. Kaynakta bulunmayan veriler None/missing olarak işaretlenir.
3. Yalnızca biçimsel ve deterministik dönüştürmeler yapılır.
"""
from typing import Any, Dict, List, Tuple
from backend.app.institutions.profile_loader import load_institution_profile, InstitutionProfile

# Opsiyonel: Profile'ı cache'lemek için (MVP)
_cached_profile: InstitutionProfile | None = None

def _get_profile(kurum_profili_id: str = "kaymakamlik") -> InstitutionProfile | None:
    global _cached_profile
    
    # Simple mapping: strip version suffixes like _v1
    base_name = kurum_profili_id.split("_v")[0] if kurum_profili_id else "kaymakamlik"
    
    # If not cached or cached profile is for a different institution, load it
    if not _cached_profile or getattr(_cached_profile, "kurum_adi", "").lower() != base_name.lower():
        try:
            _cached_profile = load_institution_profile(base_name)
        except Exception:
            pass
    return _cached_profile

def build_official_writing_context(
    draft: dict[str, Any],
    state: dict[str, Any],
    draft_type: str,
) -> dict[str, Any]:
    """
    Writing Agent draft'ı ve genel state'i okuyarak
    şablon render context'i oluşturur.

    Returns:
        {
            "context": {...},
            "missing_required_fields": [...],
            "warnings": [...],
            "source_map": {...},
            "fallback_policies": {...}
        }
    """
    context = {}
    missing = []
    warnings = []
    source_map = {}
    fallback_policies = {}

    kurum_profili_id = state.get("kurum_profili_id", "kaymakamlik")
    profile = _get_profile(kurum_profili_id)
    extraction = state.get("extraction", {})
    verified_facts = draft.get("verified_facts_used", {})

    # 1. TC BAŞLIK (tc_baslik)
    idare_adi = profile.kurum_adi if profile else None
    
    # Gönderen birim: draft'taki sender_unit'e bak.
    sender_unit_id = draft.get("sender_unit")
    birim_adi = None
    
    if sender_unit_id and profile:
        # Resolve display name from profile if possible
        # Check if it matches an id in birimler
        matched_birim = next(
            (b for b in profile.raw.get("birimler", []) 
             if b.get("id") == sender_unit_id),
            None
        )
        if matched_birim:
            birim_adi = matched_birim.get("ad")
            source_map["tc_baslik.birim_adi"] = "profile.birimler (resolved from draft.sender_unit)"
        else:
            # If not in profile but explicit in draft, maybe it's already a display name
            birim_adi = sender_unit_id
            source_map["tc_baslik.birim_adi"] = "draft.sender_unit (unresolved)"
            warnings.append(f"Sender unit '{sender_unit_id}' kurum profilinde bulunamadı.")
    
    if idare_adi and birim_adi:
        context["tc_baslik"] = {
            "idare_adi": idare_adi.upper(),
            "birim_adi": birim_adi
        }
        if "tc_baslik.idare_adi" not in source_map:
            source_map["tc_baslik.idare_adi"] = "profile.kurum_adi"
    else:
        missing.append("tc_baslik")

    # 2. SAYI & TARİH (sayi, tarih)
    # Giden evrak sayı/tarihi LLM veya agent tarafından uydurulamaz.
    context["sayi"] = ""
    missing.append("sayi")
    context["tarih"] = ""
    missing.append("tarih")

    # 3. KONU (konu)
    # Grounded subject preference
    if verified_facts and verified_facts.get("subject"):
        context["konu"] = verified_facts["subject"]
        source_map["konu"] = "verified_facts.subject"
    elif extraction.get("subject"):
        # extraction structure might be {"value": ..., "evidence": ...} or direct
        subj_data = extraction["subject"]
        context["konu"] = subj_data.get("value") if isinstance(subj_data, dict) else subj_data
        source_map["konu"] = "extraction.subject"
    elif draft.get("subject"):
        context["konu"] = draft["subject"]
        source_map["konu"] = "writing_generated.subject"
        warnings.append("Konu doğrulanamadı, generated subject kullanıldı.")
    else:
        missing.append("konu")

    # 4. MUHATAP (muhatap)
    # Outgoing recipient is NOT always incoming recipient.
    # For cevap_yazisi, we write back to the sender of the incoming document.
    recipient_name = None
    recipient_type = "kurum"

    # Writing agent might explicitly set the outbound recipient
    explicit_recipient = draft.get("recipient")
    
    if explicit_recipient:
        recipient_name = explicit_recipient
        source_map["muhatap"] = "draft.recipient (explicit)"
    elif draft_type == "cevap_yazisi":
        # The sender of the incoming document becomes the recipient
        sender_person = extraction.get("person_name", {})
        sender_inst = extraction.get("institution", {})
        
        inst_val = sender_inst.get("value") if isinstance(sender_inst, dict) else sender_inst
        person_val = sender_person.get("value") if isinstance(sender_person, dict) else sender_person

        if inst_val:
            recipient_name = inst_val
            recipient_type = "kurum"
            source_map["muhatap"] = "extraction.institution (incoming sender)"
        elif person_val:
            recipient_name = person_val
            recipient_type = "gercek_kisi"
            source_map["muhatap"] = "extraction.person_name (incoming sender)"

    if recipient_name:
        if recipient_type == "kurum":
            context["muhatap"] = {
                "tur": "kurum",
                "isim": recipient_name.upper()
            }
        else:
            context["muhatap"] = {
                "tur": "gercek_kisi",
                "isim": recipient_name
            }
    else:
        missing.append("muhatap")

    # 5. MUHATAP TÜRÜ (muhatap_turu)
    # Hiyerarşi bilinmiyorsa None bırakıyoruz.
    context["muhatap_turu"] = None
    warnings.append("Recipient hierarchy unavailable; official-writing fallback policy will be used by renderer.")
    fallback_policies["muhatap_turu"] = "unknown_hierarchy_as_kurum_ust"

    # 6. İLGİ (ilgi)
    # Sadece cevap yazısıysa, gelen belgenin tarih/sayısı ilgi tutulabilir.
    if draft_type == "cevap_yazisi":
        inc_date = extraction.get("document_date", {})
        inc_no = extraction.get("document_number", {})
        
        inc_date_val = inc_date.get("value") if isinstance(inc_date, dict) else inc_date
        inc_no_val = inc_no.get("value") if isinstance(inc_no, dict) else inc_no
        
        if inc_date_val and inc_no_val:
            context["ilgi"] = [{
                "tarih": inc_date_val,
                "sayi": inc_no_val,
                "aciklama": "ilgi yazınız" # Basic fallback, better semantic description would require verified facts
            }]
            source_map["ilgi"] = "extraction.document_date + extraction.document_number"
        else:
            missing.append("ilgi")

    # 7. METİN PARAGRAFLARI (metin_paragraflari)
    body = draft.get("body", "")
    if body:
        paragraphs = [p.strip() for p in body.split("\n") if p.strip()]
        context["metin_paragraflari"] = paragraphs
        source_map["metin_paragraflari"] = "draft.body (split)"
    else:
        missing.append("metin_paragraflari")

    # 8. İMZA (imza)
    # Sistemimizde imzalayan kişi verisi yok, uydurmayacağız.
    missing.append("imza.ad_soyad")
    missing.append("imza.unvan")

    # Diğer Opsiyonel Alanlar (ekler, iletisim, dagitim)
    # Template StrictUndefined kullandığı için en azından boş veya missing olarak tanımlanmalıdır.
    context["ekler"] = []
    context["dagitim"] = []
    context["iletisim"] = {
        "adres": "",
        "irtibat": ""
    }
    
    return {
        "context": context,
        "missing_required_fields": missing,
        "warnings": warnings,
        "source_map": source_map,
        "fallback_policies": fallback_policies
    }
