"""
WritingAgent çıktısını ve workflow state'ini resmî yazışma şablonlarının
kullandığı güvenli, tekil context sözleşmesine dönüştürür.

Kaynakta bulunmayan değerler uydurulmaz. Taslak önizlemesinin üretilebilmesi
için yalnızca açık placeholder değerleri kullanılır ve bu alanlar ayrıca
``missing_required_fields`` içinde raporlanır.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from backend.app.institutions.profile_loader import (
    InstitutionProfile,
    load_institution_profile,
)


PLACEHOLDER_SAYI = "[SAYI]"
PLACEHOLDER_IMZA_AD_SOYAD = "[AD SOYAD]"
PLACEHOLDER_IMZA_UNVAN = "[UNVAN]"
PLACEHOLDER_IDARE_ADI = "[İDARE ADI]"
PLACEHOLDER_BIRIM_ADI = "[BİRİM ADI]"
PLACEHOLDER_KONU = "[KONU]"
PLACEHOLDER_MUHATAP = "[MUHATAP]"
PLACEHOLDER_METIN = "[METİN]"

_VALID_MUHATAP_TURLERI = {
    "kurum_alt",
    "kurum_ust",
    "kurum_ayni",
    "kurum_karisik",
    "gercek_kisi",
}

_cached_profiles: dict[str, InstitutionProfile] = {}


def _get_profile(
    kurum_profili_id: str = "kaymakamlik",
) -> InstitutionProfile | None:
    """``kaymakamlik_v1`` gibi state kimliklerini profil adına çözer."""
    base_name = (
        kurum_profili_id.split("_v", 1)[0]
        if kurum_profili_id
        else "kaymakamlik"
    )

    if base_name not in _cached_profiles:
        try:
            _cached_profiles[base_name] = load_institution_profile(base_name)
        except (FileNotFoundError, ValueError):
            return None

    return _cached_profiles[base_name]


def get_extracted_value(
    extraction: dict[str, Any],
    field_name: str,
) -> Any:
    """Gerçek ``extraction.fields.<alan>.value`` sözleşmesini güvenle okur."""
    fields = extraction.get("fields", {})
    if not isinstance(fields, dict):
        return None

    field = fields.get(field_name)
    if isinstance(field, dict):
        if field.get("validated") is False:
            return None
        return field.get("value")

    # Üretim şeması dict'tir; doğrudan değer desteği yalnız güvenli geriye
    # uyumluluk içindir.
    return field


def _format_reference_date(value: Any) -> str | None:
    """Extraction'ın ISO tarihini ilgi satırı için deterministik biçimler."""
    if value is None:
        return None

    text = str(value).strip()
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        year, month, day = match.groups()
        return f"{day}.{month}.{year}"
    return text or None


def _resolve_sender_unit(
    profile: InstitutionProfile | None,
    sender_unit: Any,
) -> tuple[str | None, bool]:
    """Routing çıktısını profil içindeki resmî birim adına çözer."""
    if not sender_unit:
        return None, False

    sender_text = str(sender_unit).strip()
    if not profile:
        return sender_text, False

    for unit in profile.birimler:
        if not isinstance(unit, dict):
            continue
        if sender_text in {str(unit.get("id", "")), str(unit.get("ad", ""))}:
            return str(unit.get("ad", "")).strip() or None, True

    return sender_text, False


def _closing_for(muhatap_turu: str) -> str:
    """Template ve validator'ın paylaştığı canonical kapanışı üretir."""
    if muhatap_turu == "gercek_kisi":
        return "Saygılarımla."
    if muhatap_turu == "kurum_alt":
        return "rica ederim."
    if muhatap_turu == "kurum_karisik":
        return "arz ve rica ederim."
    return "arz ederim."


def build_official_writing_context(
    draft: dict[str, Any],
    state: dict[str, Any],
    draft_type: str,
) -> dict[str, Any]:
    """Writing draft + workflow state'ten güvenli template context'i kurar."""
    context: dict[str, Any] = {}
    missing: list[str] = []
    warnings: list[str] = []
    source_map: dict[str, str] = {}
    fallback_policies: dict[str, str] = {}

    extraction = state.get("extraction", {})
    if not isinstance(extraction, dict):
        extraction = {}
    routing = state.get("routing", {})
    if not isinstance(routing, dict):
        routing = {}

    kurum_profili_id = state.get("kurum_profili_id", "kaymakamlik_v1")
    profile = _get_profile(str(kurum_profili_id))

    # 1. T.C. başlık ve gönderen birim. Workflow'un canonical kaynağı
    # routing.recommended_unit'tir; draft.sender_unit yalnız geriye uyumludur.
    idare_adi = profile.kurum_adi if profile else None
    if idare_adi:
        source_map["tc_baslik.idare_adi"] = "institution_profile.kurum_adi"
    else:
        idare_adi = PLACEHOLDER_IDARE_ADI
        missing.append("tc_baslik.idare_adi")

    routing_unit = routing.get("recommended_unit")
    sender_unit = routing_unit or draft.get("sender_unit")
    birim_adi, unit_resolved = _resolve_sender_unit(profile, sender_unit)

    if birim_adi:
        if routing_unit:
            source_map["tc_baslik.birim_adi"] = "routing.recommended_unit"
        else:
            source_map["tc_baslik.birim_adi"] = "draft.sender_unit"
        if unit_resolved:
            source_map["tc_baslik.birim_adi"] += " -> institution_profile.birimler"
        else:
            warnings.append(
                f"Sender unit '{birim_adi}' kurum profilinde bulunamadı."
            )
    else:
        birim_adi = PLACEHOLDER_BIRIM_ADI
        missing.append("tc_baslik.birim_adi")

    context["tc_baslik"] = {
        "idare_adi": str(idare_adi).upper(),
        "birim_adi": birim_adi,
    }

    # 2. Giden evrak sayı/tarihi incoming belgeden devralınamaz.
    context["sayi"] = PLACEHOLDER_SAYI
    context["tarih"] = datetime.now().strftime("%d.%m.%Y")
    missing.append("sayi")
    source_map["sayi"] = "placeholder: outgoing EBYS metadata unavailable"
    source_map["tarih"] = "system.datetime.now"

    # 3. Konu: doğrulanmış extraction alanı, ardından WritingAgent taslağı.
    extracted_subject = get_extracted_value(extraction, "subject")
    if extracted_subject:
        context["konu"] = str(extracted_subject).strip()
        source_map["konu"] = "extraction.fields.subject.value"
    elif draft.get("subject"):
        context["konu"] = str(draft["subject"]).strip()
        source_map["konu"] = "draft.subject"
        warnings.append("Konu extraction ile doğrulanamadı; WritingAgent konusu kullanıldı.")
    else:
        context["konu"] = PLACEHOLDER_KONU
        missing.append("konu")

    # 4. Muhatap. Açık Writing/state muhatabı korunur; extraction için gerçek
    # alan önceliği recipient -> institution -> person_name şeklindedir.
    person_name = get_extracted_value(extraction, "person_name")
    institution = get_extracted_value(extraction, "institution")
    extracted_recipient = get_extracted_value(extraction, "recipient")
    state_muhatap = state.get("muhatap")

    recipient_name: Any = None
    recipient_kind = "kurum"

    if isinstance(state_muhatap, dict) and state_muhatap.get("isim"):
        recipient_name = state_muhatap["isim"]
        recipient_kind = (
            "gercek_kisi"
            if state_muhatap.get("tur") == "gercek_kisi"
            else "kurum"
        )
        source_map["muhatap"] = "state.muhatap"
    elif draft.get("recipient"):
        recipient_name = draft["recipient"]
        recipient_text = str(recipient_name).strip()
        if extracted_recipient and recipient_text == str(extracted_recipient).strip():
            source_map["muhatap"] = "extraction.fields.recipient.value"
        elif institution and recipient_text == str(institution).strip():
            source_map["muhatap"] = "extraction.fields.institution.value"
        elif person_name and recipient_text == str(person_name).strip():
            source_map["muhatap"] = "extraction.fields.person_name.value"
            recipient_kind = "gercek_kisi"
        else:
            source_map["muhatap"] = "draft.recipient"
    elif extracted_recipient:
        recipient_name = extracted_recipient
        source_map["muhatap"] = "extraction.fields.recipient.value"
    elif institution:
        recipient_name = institution
        source_map["muhatap"] = "extraction.fields.institution.value"
    elif person_name:
        recipient_name = person_name
        recipient_kind = "gercek_kisi"
        source_map["muhatap"] = "extraction.fields.person_name.value"

    if recipient_name:
        recipient_text = str(recipient_name).strip()
        context["muhatap"] = {
            "tur": recipient_kind,
            "isim": (
                recipient_text.upper()
                if recipient_kind == "kurum"
                else recipient_text
            ),
        }
    else:
        context["muhatap"] = {
            "tur": "kurum",
            "isim": PLACEHOLDER_MUHATAP,
        }
        missing.append("muhatap")

    explicit_hierarchy = state.get("muhatap_turu")
    if explicit_hierarchy in _VALID_MUHATAP_TURLERI:
        muhatap_turu = str(explicit_hierarchy)
        source_map["muhatap_turu"] = "state.muhatap_turu"
    elif recipient_kind == "gercek_kisi":
        muhatap_turu = "gercek_kisi"
        source_map["muhatap_turu"] = "derived_from_muhatap.tur"
    else:
        muhatap_turu = "kurum_ust"
        fallback_policies["muhatap_turu"] = "unknown_hierarchy_as_kurum_ust"
        warnings.append(
            "Muhatap kurum hiyerarşisi bilinmiyor; canonical üst makam "
            "fallback kapanışı kullanıldı."
        )

    context["muhatap_turu"] = muhatap_turu
    context["kapalis_ifadesi"] = _closing_for(muhatap_turu)
    source_map["kapalis_ifadesi"] = "derived_from_context.muhatap_turu"

    # 5. İlgi: yalnız gelen belgenin güvenilir tarih/sayı alanlarından.
    context["ilgi"] = []
    if draft_type == "cevap_yazisi":
        incoming_date = _format_reference_date(
            get_extracted_value(extraction, "document_date")
        )
        incoming_number = get_extracted_value(extraction, "document_number")

        if incoming_date and incoming_number:
            context["ilgi"] = [{
                "tarih": incoming_date,
                "sayi": str(incoming_number).strip(),
                "aciklama": "ilgi yazınız",
            }]
            source_map["ilgi"] = (
                "extraction.fields.document_date.value + "
                "extraction.fields.document_number.value"
            )
        else:
            missing.append("ilgi")
            warnings.append(
                "Başvurunun doğrulanmış tarih ve sayısı birlikte bulunmadığı "
                "için ilgi satırı uydurulmadan çıkarıldı."
            )

    # 6. Gövde.
    body = str(draft.get("body") or "").strip()
    if body:
        context["metin_paragraflari"] = [
            paragraph.strip()
            for paragraph in body.splitlines()
            if paragraph.strip()
        ]
        source_map["metin_paragraflari"] = "draft.body"
    else:
        context["metin_paragraflari"] = [PLACEHOLDER_METIN]
        missing.append("metin_paragraflari")

    # 7. İmzalayan kişi workflow'da bulunmuyor. Açık placeholder kullanılır.
    context["imza"] = {
        "ad_soyad": PLACEHOLDER_IMZA_AD_SOYAD,
        "unvan": PLACEHOLDER_IMZA_UNVAN,
        "yetki_turu": "normal",
    }
    missing.extend(["imza.ad_soyad", "imza.unvan"])
    source_map["imza.ad_soyad"] = "placeholder: signer unavailable"
    source_map["imza.unvan"] = "placeholder: signer title unavailable"

    # 8. Aktif template'lerin opsiyonel değişkenleri de StrictUndefined için
    # açıkça tanımlanır. Incoming adres/ek verileri outgoing metadata sayılmaz.
    context["ekler"] = []
    context["dagitim"] = None
    context["iletisim"] = {"adres": "", "irtibat": ""}
    context["sayfa_no"] = None
    context["uygunsuz_belge_uyarisi"] = None

    missing = list(dict.fromkeys(missing))
    if missing:
        warnings.append(
            "Taslak önizlemesinde eksik alanlar açık placeholder olarak "
            "gösterildi; personel/EBYS tarafından tamamlanmalıdır."
        )

    return {
        "context": context,
        "missing_required_fields": missing,
        "warnings": warnings,
        "source_map": source_map,
        "fallback_policies": fallback_policies,
    }
