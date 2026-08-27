def check_permission(mode: str, user_context: dict, workflow_context: dict) -> tuple[bool, str | None]:
    """
    Returns (allowed, denial_message). Pure function, no LLM call.
    Enforces RBAC matrix for copilot actions.
    """
    # Okuma modları için şimdilik genelde izin ver
    if mode not in ("workflow_action", "clarification_action", "taslak_duzenleme"):
        return True, None
        
    if not user_context:
        # Geriye dönük uyumluluk (eski testler taslak_duzenleme'yi user_context olmadan çağırıyor)
        if mode == "taslak_duzenleme":
            return True, None
        return False, "Oturum süresi dolmuş veya geçersiz. Lütfen tekrar giriş yapın."
        
    role = user_context.get("role")
    department = user_context.get("department")
        
    analysis_state = workflow_context.get("analysis_state", {})
    case_department = analysis_state.get("department")  # Assuming case has a department owner
    
    if mode == "workflow_action":
        if role == "EVRAK_KAYIT":
            # EVRAK_KAYIT can route things, but cannot act on behalf of a specific department's internal cases
            # If the case is already assigned to a department and EVRAK_KAYIT tries to approve it, deny.
            if case_department and case_department != "Yazı İşleri" and case_department != department:
                return False, "Yetki Hatası: Başka bir birime atanmış evrak üzerinde işlem yapamazsınız."
            return True, None
        elif role == "BIRIM_PERSONELI":
            return True, None
            
    if mode == "taslak_duzenleme" or mode == "clarification_action":
        if role == "EVRAK_KAYIT":
            return False, "Yetki Hatası: Evrak Kayıt personeli taslak düzenleme veya ek bilgi talebi işlemlerini yapamaz."
        elif role == "BIRIM_PERSONELI":
            if case_department and case_department != department:
                return False, "Yetki Hatası: Sadece kendi biriminizdeki dosyalar üzerinde işlem yapabilirsiniz."
            return True, None

    return True, None
