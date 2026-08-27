def get_dummy_user_context() -> dict:
    """
    [DEMO] Returns a dummy user context for Copilot RBAC enforcement.
    When the actual auth branch is merged, this adapter should be updated
    or replaced to extract the user from the JWT token.
    """
    return {
        "role": "EVRAK_KAYIT",
        "department": "Yazı İşleri",
        "name": "Test User"
    }
