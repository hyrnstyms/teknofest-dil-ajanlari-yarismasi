"""
backend/app/institutions/__init__.py
Kurum profili yükleme altyapısı.
"""
from backend.app.institutions.profile_loader import load_institution_profile, InstitutionProfile

__all__ = ["load_institution_profile", "InstitutionProfile"]
