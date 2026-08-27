"""
renderers/template_renderer.py
──────────────────────────────────────────────────────────────────────────────
Merkezi Jinja2 Render Modülü

AMAÇ:
  Şablonları render edecek TEK giriş noktasıdır.  Ajan 6 (ve diğer
  ajanlar) doğrudan Jinja2 Environment açmak yerine bu modülün
  fonksiyonlarını çağırmalıdır.  Böylece aşağıdaki güvenlik kısıtları
  tüm çağrıcılara otomatik olarak uygulanır:

    1. StrictUndefined — tanımsız değişken sessizce boş string olmaz,
       anında UndefinedError fırlatır.
    2. gun zorunluluğu — tekit yazısında gun parametresi eksikse,
       Jinja2'nin UndefinedError'ına ek olarak render öncesinde
       açıklayıcı bir ValueError kaldırılır.
    3. cevap yazısında ilgi zorunluluğu — [TASARIM KARARI] gereği,
       render öncesinde kontrol edilir.

  Bu modül DÜZ METİN (str) döndürür.  PDF/DOCX dönüşümü ayrı bir
  katmanda yapılmalıdır.

KULLANIM (Ajan 6 için):
    from renderers.template_renderer import render_ust_yazi, render_cevap_yazisi, render_tekit_yazisi

    metin = render_ust_yazi(context_dict)
    metin = render_cevap_yazisi(context_dict)   # ilgi zorunlu
    metin = render_tekit_yazisi(context_dict)   # gun zorunlu

NOTLAR:
  - Environment singleton'dır; import başına bir kez oluşturulur.
  - Şablon dosya yolu: proje kökündeki templates/ dizini.
    templates/ dizini bu modülün konumuna göre otomatik bulunur.
"""

from __future__ import annotations

import pathlib
import re
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

# ──────────────────────────────────────────────────────────────────────────────
# Jinja2 Environment — SINGLETON
# StrictUndefined burada merkezi olarak kilitlenmiştir.
# Bu environment'ı bypass eden kod, modülün sağladığı güvencelerden yoksun
# kalır.  Ajan 6 bu env'i doğrudan kullanmak yerine aşağıdaki
# render_* fonksiyonlarını tercih etmelidir.
# ──────────────────────────────────────────────────────────────────────────────

_TEMPLATES_DIR = pathlib.Path(__file__).parent / "templates"

_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    undefined=StrictUndefined,   # tanımsız değişken → UndefinedError
    keep_trailing_newline=True,
)


# Times New Roman 12pt'te bir boşluk yaklaşık 3pt genişliğindedir.
# 1,25 cm = 35,43pt olduğundan düz metin önizlemesinde 12 sabit boşluk,
# checklist'teki 1,25 cm paragraf girintisinin en yakın temsilidir.
_PARAGRAPH_INDENT = " " * 12


def _normalize_official_layout(rendered: str) -> str:
    """Şablon çıktısındaki yalnızca resmî yazı yerleşim boşluklarını düzelt."""
    lines = rendered.strip("\n").splitlines()
    govde_indexes = [
        index for index, line in enumerate(lines) if line.startswith("\t")
    ]
    govde_index = govde_indexes[0] if govde_indexes else None
    govde_son_index = govde_indexes[-1] if govde_indexes else None
    lines = [re.sub(r"^\t", _PARAGRAPH_INDENT, line) for line in lines]

    def find_line(predicate, start: int = 0) -> int | None:
        for index in range(start, len(lines)):
            if predicate(lines[index]):
                return index
        return None

    def previous_content(index: int) -> int | None:
        for candidate in range(index - 1, -1, -1):
            if lines[candidate].strip():
                return candidate
        return None

    def set_blank_lines(left: int | None, right: int | None, count: int) -> None:
        if left is None or right is None or left >= right:
            return
        if any(line.strip() for line in lines[left + 1:right]):
            return
        lines[left + 1:right] = [""] * count

    sayi_index = find_line(lambda line: line.startswith("Sayı:"))
    konu_index = find_line(lambda line: line.startswith("Konu:"))
    baslik_son_index = previous_content(sayi_index) if sayi_index is not None else None
    ilgi_indexes = [
        index for index, line in enumerate(lines) if line.startswith("İlgi:")
    ]
    ek_index = find_line(
        lambda line: line.startswith("Ek:") or line.startswith("Ek konulmadı")
    )
    dagitim_index = find_line(lambda line: line.startswith("Dağıtım:"))

    imza_son_index = previous_content(ek_index) if ek_index is not None else None
    imza_ilk_index = imza_son_index
    while (
        imza_ilk_index is not None
        and imza_ilk_index > 0
        and lines[imza_ilk_index - 1].strip()
    ):
        imza_ilk_index -= 1
    imza_oncesi_index = (
        previous_content(imza_ilk_index) if imza_ilk_index is not None else None
    )
    muhatap_index = None
    if konu_index is not None:
        bounds = [
            index for index in [ilgi_indexes[0] if ilgi_indexes else None, govde_index]
            if index is not None
        ]
        upper_bound = min(bounds, default=len(lines))
        muhatap_index = find_line(lambda line: bool(line.strip()), konu_index + 1)
        if muhatap_index is not None and muhatap_index >= upper_bound:
            muhatap_index = None

    # Aşağıdan yukarı çalışmak indeks kaymalarının diğer sınırları etkilemesini önler.
    set_blank_lines(ek_index, dagitim_index, 2)
    set_blank_lines(imza_son_index, ek_index, 2)
    set_blank_lines(imza_oncesi_index, imza_ilk_index, 2)
    if (
        govde_son_index is not None
        and imza_oncesi_index is not None
        and imza_oncesi_index != govde_son_index
    ):
        set_blank_lines(govde_son_index, imza_oncesi_index, 0)
    if govde_index is not None:
        govde_oncesi = ilgi_indexes[-1] if ilgi_indexes else muhatap_index
        set_blank_lines(govde_oncesi, govde_index, 1 if ilgi_indexes else 2)
    if ilgi_indexes:
        set_blank_lines(muhatap_index, ilgi_indexes[0], 2)
    set_blank_lines(konu_index, muhatap_index, 2)
    set_blank_lines(sayi_index, konu_index, 0)
    set_blank_lines(baslik_son_index, sayi_index, 2)

    return "\n".join(lines).rstrip() + "\n"


def get_env() -> Environment:
    """
    Merkezi Jinja2 Environment'ı döndürür.

    Test fixture'ları bu fonksiyonu kullanarak environment'ı almalıdır;
    böylece test ve üretim ortamı aynı konfigürasyonu paylaşır.
    """
    return _ENV


# ──────────────────────────────────────────────────────────────────────────────
# Render Fonksiyonları
# ──────────────────────────────────────────────────────────────────────────────


def render_ust_yazi(context: dict[str, Any]) -> str:
    """
    ust_yazi.jinja2 şablonunu render eder ve düz metin döndürür.

    Parametreler için: templates/ust_yazi.jinja2 dosyasının başlığına bakınız.
    Bilgilendirme yazısı da bu fonksiyonu kullanır (ayrı şablon yoktur).

    Raises:
        UndefinedError: context'te zorunlu bir alan eksikse.
    """
    tmpl = _ENV.get_template("ust_yazi.jinja2")
    return _normalize_official_layout(tmpl.render(**context))


def render_cevap_yazisi(context: dict[str, Any]) -> str:
    """
    cevap_yazisi.jinja2 şablonunu render eder ve düz metin döndürür.

    İlgi yalnızca doğrulanmış başvuru tarihi ve sayısı mevcutsa gösterilir.
    Kaynak veride bu bilgiler yoksa şablon ilgi satırı olmadan render edilir.

    Raises:
        UndefinedError: context'te başka zorunlu bir alan eksikse.
    """
    tmpl = _ENV.get_template("cevap_yazisi.jinja2")
    return _normalize_official_layout(tmpl.render(**context))


def render_tekit_yazisi(context: dict[str, Any]) -> str:
    """
    tekit_yazisi.jinja2 şablonunu render eder ve düz metin döndürür.

    'gun' parametresi ZORUNLUDUR; varsayılan değeri yoktur.
    Kılavuz Örnek 24'teki '5 gün' ifadesi tek bir örnek senaryodur;
    Madde 34 sayısal bir süre belirtmez.  Bu yüzden render öncesinde
    açıklayıcı bir ValueError kaldırılır — StrictUndefined'ın
    soyut UndefinedError'ının yerine geçmesi için.

    'ilgi' alanı da Madde 34 gereği zorunludur; render öncesinde
    kontrol edilir.

    Raises:
        ValueError:     'gun' veya 'ilgi' eksikse.
        UndefinedError: context'te başka zorunlu bir alan eksikse.
    """
    # gun zorunluluk kontrolü — StrictUndefined UndefinedError yerine
    # açıklayıcı ValueError kaldırılır ki Ajan 6 neyi eksik bıraktığını
    # derhal anlasın.
    if "gun" not in context or context["gun"] is None:
        raise ValueError(
            "Tekit yazısında 'gun' parametresi zorunludur; varsayılan yoktur. "
            "Kılavuz Örnek 24'teki '5 gün' ifadesi tek bir örnek senaryodur "
            "(Madde 34 sayısal bir süre belirtmez). "
            "Kaç günde cevap beklediğinizi açıkça belirtin."
        )

    # ilgi zorunluluk kontrolü (Madde 34)
    ilgi = context.get("ilgi")
    if not ilgi:
        raise ValueError(
            "Tekit yazısında 'ilgi' alanı zorunludur (Madde 34). "
            "Önceki yazının tarih ve sayısını context'e ekleyin."
        )

    tmpl = _ENV.get_template("tekit_yazisi.jinja2")
    return _normalize_official_layout(tmpl.render(**context))
