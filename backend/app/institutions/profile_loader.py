"""
backend/app/institutions/profile_loader.py
──────────────────────────────────────────────────────────────────────────────
Kurum Profili YAML Yükleyici

AMAÇ:
  Farklı kamu kurumları için hazırlanmış YAML profil dosyalarını okur.
  Şu an için kaymakamlik profili bulunmaktadır.

KULLANIM:
    from backend.app.institutions.profile_loader import load_institution_profile
    profil = load_institution_profile("kaymakamlik")

ÖNEMLİ:
  - Bu modül hiçbir LLM çağrısı yapmaz.
  - Routing Agent hâlâ data/routing/unit_registry.json kullanmaktadır;
    bu yükleyici geleceğe yönelik kurum profili altyapısını hazırlar.
  - YAML içindeki yasal_dayanak gibi metadata değerleri Legal Agent'a
    doğrulanmış hukuki evidence olarak VERİLMEMELİDİR.
    Legal Agent kendi evidence-validation mantığını korur.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from typing import Any


# Kurum profil YAML dosyalarının bulunduğu kök dizin
_INSTITUTIONS_DATA_DIR = (
    pathlib.Path(__file__).parent.parent.parent.parent  # proje kökü
    / "data"
    / "institutions"
)


@dataclass
class InstitutionProfile:
    """
    Yüklenmiş kurum profilini temsil eder.
    """
    kurum_adi: str = ""
    kurum_turu: str = ""
    birimler: list[dict[str, Any]] = field(default_factory=list)
    evrak_turleri: list[dict[str, Any]] = field(default_factory=list)
    yazi_turleri: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml_dict(cls, data: dict[str, Any]) -> "InstitutionProfile":
        """Ham YAML dict'ten InstitutionProfile oluşturur."""
        kurum = data.get("kurum", {})
        return cls(
            kurum_adi=str(kurum.get("ad", "")),
            kurum_turu=str(kurum.get("tur", "")),
            birimler=list(data.get("birimler", [])),
            evrak_turleri=list(data.get("evrak_turleri", [])),
            yazi_turleri=list(data.get("yazi_turleri", [])),
            raw=data,
        )


def load_institution_profile(
    kurum_adi: str,
    profiles_dir: pathlib.Path | None = None,
) -> InstitutionProfile:
    """
    Belirtilen kurum için YAML profil dosyasını yükler.

    Args:
        kurum_adi: Kurum klasör adı (ör. "kaymakamlik").
                   Dosya yolu: data/institutions/<kurum_adi>/kurum_profili_<kurum_adi>.yaml
        profiles_dir: Opsiyonel override; varsayılan data/institutions/ dir.

    Returns:
        InstitutionProfile nesnesi.

    Raises:
        FileNotFoundError: Profil dosyası bulunamazsa.
        ValueError:        YAML parse hatası varsa.
    """
    import yaml  # PyYAML zaten requirements.txt'te mevcut

    base_dir = profiles_dir or _INSTITUTIONS_DATA_DIR
    profile_path = base_dir / kurum_adi / f"kurum_profili_{kurum_adi}.yaml"

    if not profile_path.exists():
        raise FileNotFoundError(
            f"Kurum profil dosyası bulunamadı: {profile_path}\n"
            f"Beklenen konum: data/institutions/{kurum_adi}/kurum_profili_{kurum_adi}.yaml"
        )

    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(
            f"Kurum profil dosyası parse edilemedi: {profile_path}\nHata: {exc}"
        ) from exc

    if not isinstance(raw_data, dict):
        raise ValueError(
            f"Kurum profil dosyası geçersiz format (dict bekleniyor): {profile_path}"
        )

    return InstitutionProfile.from_yaml_dict(raw_data)


def list_available_profiles(
    profiles_dir: pathlib.Path | None = None,
) -> list[str]:
    """
    data/institutions/ altındaki mevcut kurum profil klasörlerini listeler.

    Returns:
        Kurum adlarının listesi (ör. ["kaymakamlik"]).
    """
    base_dir = profiles_dir or _INSTITUTIONS_DATA_DIR

    if not base_dir.exists():
        return []

    return [
        p.name
        for p in base_dir.iterdir()
        if p.is_dir() and (p / f"kurum_profili_{p.name}.yaml").exists()
    ]
