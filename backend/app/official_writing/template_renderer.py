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
    return tmpl.render(**context)


def render_cevap_yazisi(context: dict[str, Any]) -> str:
    """
    cevap_yazisi.jinja2 şablonunu render eder ve düz metin döndürür.

    [TASARIM KARARI] ilgi zorunludur — render öncesinde kontrol edilir.
    Yönetmelikte cevap yazısı için ilgi zorunluluğu kaynaklı değildir;
    ekip kararıdır (tekit yazısı için Madde 34'te kaynaklıdır).

    Raises:
        ValueError:     context['ilgi'] eksik veya boşsa.
        UndefinedError: context'te başka zorunlu bir alan eksikse.
    """
    ilgi = context.get("ilgi")
    if not ilgi:
        raise ValueError(
            "[TASARIM KARARI] Cevap yazısında 'ilgi' alanı zorunludur. "
            "Cevap verilen yazının tarih ve sayısı context'e ekleyin. "
            "(Not: bu zorunluluk yönetmelikte kaynaklı değil, ekip kararıdır.)"
        )
    tmpl = _ENV.get_template("cevap_yazisi.jinja2")
    return tmpl.render(**context)


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
    return tmpl.render(**context)
