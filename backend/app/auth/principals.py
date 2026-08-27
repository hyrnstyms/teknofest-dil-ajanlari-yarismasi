"""Demo principals. Roles are never taken from client request bodies."""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.cases.enums import ROLE_BIRIM_PERSONELI, ROLE_EVRAK_KAYIT

AYSE_KAYA_ID = "a1e0a1e0-1111-4111-8111-000000000001"
MEHMET_DEMIR_ID = "b2e0b2e0-2222-4222-8222-000000000002"
SELIN_AKSOY_ID = "c3e0c3e0-3333-4333-8333-000000000003"
MURAT_CELIK_ID = "d4e0d4e0-4444-4444-8444-000000000004"


@dataclass(frozen=True)
class DemoPrincipal:
    id: str
    user_key: str
    name: str
    role: str
    institution_id: str
    department_code: str


DEMO_USERS: dict[str, DemoPrincipal] = {
    "ayse_kaya": DemoPrincipal(
        id=AYSE_KAYA_ID,
        user_key="ayse_kaya",
        name="Ayşe Kaya",
        role=ROLE_EVRAK_KAYIT,
        institution_id="belediye",
        department_code="yazi_isleri",
    ),
    "mehmet_demir": DemoPrincipal(
        id=MEHMET_DEMIR_ID,
        user_key="mehmet_demir",
        name="Mehmet Demir",
        role=ROLE_BIRIM_PERSONELI,
        institution_id="belediye",
        department_code="fen_isleri",
    ),
    "selin_aksoy": DemoPrincipal(
        id=SELIN_AKSOY_ID,
        user_key="selin_aksoy",
        name="Selin Aksoy",
        role=ROLE_EVRAK_KAYIT,
        institution_id="kaymakamlik",
        department_code="yazi_isleri",
    ),
    "murat_celik": DemoPrincipal(
        id=MURAT_CELIK_ID,
        user_key="murat_celik",
        name="Murat Çelik",
        role=ROLE_BIRIM_PERSONELI,
        institution_id="kaymakamlik",
        department_code="milli_egitim",
    ),
}
