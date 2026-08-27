"""Canonical role/department checks for Copilot suggestions."""

from __future__ import annotations


def check_permission(
    mode: str,
    user_context: dict,
    workflow_context: dict,
) -> tuple[bool, str | None]:
    write_modes = {"workflow_action", "clarification_action", "taslak_duzenleme"}
    if mode not in write_modes:
        return True, None
    if not user_context:
        # Preserve legacy analysis draft editing while requiring authentication
        # for every Case mutation.
        if mode == "taslak_duzenleme" and not workflow_context.get("case_id"):
            return True, None
        return False, "Oturum geçersiz. Lütfen tekrar giriş yapın."

    role = user_context.get("role")
    department_code = user_context.get("department_code")
    state = workflow_context.get("analysis_state") or {}
    case_department_code = state.get("current_department_code")

    if mode == "clarification_action":
        if role != "EVRAK_KAYIT":
            return False, "Yetki Hatası: Eksik bilgi talebini Evrak Kayıt personeli onaylar."
        return True, None

    if mode == "taslak_duzenleme":
        if role != "BIRIM_PERSONELI":
            return False, "Yetki Hatası: Resmî cevap taslağını yalnız Birim Personeli düzenleyebilir."
        if case_department_code and case_department_code != department_code:
            return False, "Yetki Hatası: Yalnız kendi biriminizdeki dosyalar üzerinde işlem yapabilirsiniz."
        return True, None

    if mode == "workflow_action":
        if role not in {"EVRAK_KAYIT", "BIRIM_PERSONELI"}:
            return False, "Yetki Hatası: Bu rol Case iş akışını değiştiremez."
        if (
            role == "BIRIM_PERSONELI"
            and case_department_code
            and case_department_code != department_code
        ):
            return False, "Yetki Hatası: Yalnız kendi biriminizdeki dosyalar üzerinde işlem yapabilirsiniz."
        return True, None

    return False, "Yetki Hatası: İşleme izin verilmedi."
