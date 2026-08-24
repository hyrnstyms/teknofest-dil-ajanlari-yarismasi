"""
backend/app/official_writing/__init__.py
Official Writing modülü – resmî yazı biçim doğrulama, şablon render ve DOCX üretimi.
"""
from backend.app.official_writing.format_validator import validate_format, DogrulamaSonucu
from backend.app.official_writing.template_renderer import (
    render_ust_yazi,
    render_cevap_yazisi,
    render_tekit_yazisi,
    get_env,
)
from backend.app.official_writing.docx_renderer import render_to_docx

__all__ = [
    "validate_format",
    "DogrulamaSonucu",
    "render_ust_yazi",
    "render_cevap_yazisi",
    "render_tekit_yazisi",
    "get_env",
    "render_to_docx",
]
