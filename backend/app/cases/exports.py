"""Approved CaseDraft exports using the existing official-writing contract."""
from __future__ import annotations

import html
import io
from typing import Any

from fastapi import HTTPException

from backend.app.official_writing.context_adapter import build_official_writing_context
from backend.app.official_writing.docx_renderer import generate_qr_image, render_to_docx


def approved_export_context(aggregate: dict[str, Any], draft_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    draft = next((item for item in aggregate.get("drafts", []) if item.get("id") == draft_id), None)
    if draft is None:
        raise HTTPException(status_code=404, detail={"code": "draft_not_found", "message": "Taslak bulunamadı."})
    if draft.get("status") != "APPROVED":
        raise HTTPException(status_code=409, detail={"code": "approved_draft_required", "message": "Dışa aktarma için taslak onayı gerekir."})
    case = aggregate["case"]
    analysis = aggregate.get("analysis") or {}
    content = dict(draft.get("content") or {})
    extraction = dict(analysis.get("extraction") or {})
    extraction_fields = dict(extraction.get("fields") or {})
    # An approved human revision is authoritative for editable outgoing
    # document fields. Incoming extraction remains evidence, but must not
    # overwrite the subject the reviewer explicitly approved.
    extraction_fields.pop("subject", None)
    extraction["fields"] = extraction_fields
    state = {
        "kurum_profili_id": case.get("institution_id"),
        "routing": analysis.get("routing") or {"recommended_unit": case.get("current_department_code")},
        "extraction": extraction,
        "muhatap": {"tur": "gercek_kisi" if case.get("originator_type") == "VATANDAS" else "kurum", "isim": case.get("originator_name")},
    }
    built = build_official_writing_context(content, state, "cevap_yazisi")
    return built["context"], draft


def render_case_pdf(context: dict[str, Any], verification_value: str) -> io.BytesIO:
    """Render a compact A4 PDF without invoking an office suite or model."""
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - deployment dependency guard
        raise HTTPException(status_code=503, detail={"code": "pdf_renderer_unavailable", "message": "PDF oluşturucu hazır değil."}) from exc

    heading = context.get("tc_baslik") or {}
    recipient = context.get("muhatap") or {}
    paragraphs = context.get("metin_paragraflari") or []
    body = "".join(f"<p>{html.escape(str(value))}</p>" for value in paragraphs)
    markup = f"""<div style='font-family: sans-serif; font-size: 11pt; line-height: 1.5'>
      <p style='text-align:center'><b>T.C.<br>{html.escape(str(heading.get('idare_adi','')))}<br>{html.escape(str(heading.get('birim_adi','')))}</b></p>
      <p><b>Sayı:</b> {html.escape(str(context.get('sayi','')))} <span style='float:right'><b>Tarih:</b> {html.escape(str(context.get('tarih','')))}</span></p>
      <p><b>Konu:</b> {html.escape(str(context.get('konu','')))}</p>
      <p style='text-align:center'><b>{html.escape(str(recipient.get('isim','')))}</b></p>
      {body}
      <p style='text-align:right'><b>{html.escape(str((context.get('imza') or {}).get('ad_soyad','')))}</b><br>{html.escape(str((context.get('imza') or {}).get('unvan','')))}</p>
      <p style='font-size:8pt;color:#475569'>Bu belge EVRAG vaka kaydı üzerinden doğrulanabilir.</p>
    </div>"""
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_htmlbox(fitz.Rect(55, 45, 540, 790), markup)
    qr = generate_qr_image(verification_value).getvalue()
    page.insert_image(fitz.Rect(455, 710, 525, 780), stream=qr)
    output = io.BytesIO(document.tobytes(deflate=True))
    document.close()
    output.seek(0)
    return output
