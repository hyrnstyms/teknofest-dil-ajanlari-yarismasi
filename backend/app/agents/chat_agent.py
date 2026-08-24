"""LLM kullanmadan kullanım kılavuzu sorularını yanıtlayan SSS ajanı."""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import TYPE_CHECKING

from rapidfuzz import fuzz

if TYPE_CHECKING:
    from backend.app.agents.legal_agent import LegalAgent


ESLESME_ESIGI = 70

FALLBACK_MESAJI = (
    "Bu konuda size yardımcı olamadım. Sorunuzu farklı şekilde ifade edebilir "
    "veya bir mevzuat sorusu soruyorsanız doğrudan kanun/madde belirterek "
    "sorabilirsiniz."
)

MEVZUAT_SORUSU_RE = re.compile(
    r"\b(?:kanun\w*|madde\w*|yönetmeli\w*|yonetmeli\w*|sayılı\w*|sayili\w*)\b",
    flags=re.UNICODE,
)

MEVZUAT_SERVIS_HATASI_MESAJI = (
    "Mevzuat arama hizmetine şu anda ulaşılamıyor. Lütfen daha sonra tekrar "
    "deneyin."
)

MEVZUAT_KANIT_BULUNAMADI_MESAJI = (
    "Sağlanan kaynaklarda soruya ilişkin doğrulanabilir bir bilgi çıkarılamadı."
)


SSS_LISTESI: list[dict[str, str]] = [
    {
        "soru": "Bu sistem ne işe yarıyor?",
        "cevap": (
            "Kamu kurumuna gelen evrakları (dilekçe, resmî yazı vb.) otomatik "
            "olarak okuyup sınıflandırır, ilgili mevzuatı bulur, eksik bilgileri "
            "tespit eder, hangi birime gitmesi gerektiğini önerir ve resmî yazı "
            "taslağı hazırlar. Nihai karar her zaman personelde kalır."
        ),
    },
    {
        "soru": "Evrak nasıl yüklerim?",
        "cevap": (
            "Belge Girişi alanına dosyayı sürükleyip bırakabilir, alana tıklayarak "
            "dosya seçebilir veya metni doğrudan yapıştırabilirsiniz. Ardından "
            "'Belgeyi Analiz Et' düğmesine tıklayın."
        ),
    },
    {
        "soru": "Hangi dosya türlerini yükleyebilirim?",
        "cevap": (
            "Ana Belge Girişi alanı PDF, PNG, JPG, JPEG ve TIFF dosyalarını kabul "
            "eder. Dosya yerine evrak metnini de doğrudan yapıştırabilirsiniz."
        ),
    },
    {
        "soru": "Belgeyi Analiz Et ne yapar?",
        "cevap": (
            "Seçtiğiniz dosyayı veya yapıştırdığınız metni analiz sürecine gönderir. "
            "İşlem sürerken düğmede 'Analiz Ediliyor...' ifadesi görünür."
        ),
    },
    {
        "soru": "Analiz aşamaları nelerdir?",
        "cevap": (
            "Süreç göstergesinde sırasıyla Evrak Analizi, Bilgi Çıkarımı, Mevzuat "
            "Analizi, Eksik Kontrolü, Özetleme, Birim Yönlendirme, Resmî Yazı "
            "Hazırlama ve Kalite Kontrol aşamaları gösterilir."
        ),
    },
    {
        "soru": "API, Mevzuat DB ve LLM durumları neyi gösterir?",
        "cevap": (
            "Üst bölümdeki rozetler API'nin, mevzuat veritabanının ve dil modeli "
            "hizmetinin erişilebilirlik durumunu gösterir. Aktif, Hata, Erişilemiyor "
            "veya Bekliyor ifadeleri ilgili servisin o anki durumudur."
        ),
    },
    {
        "soru": "Evrak Analizi bölümünde ne görüyorum?",
        "cevap": (
            "Evrak Türü, İşlem Niyeti ve varsa analize ait Belge ID bilgilerini "
            "görürsünüz. Bir değer üretilemezse 'Belirsiz' veya analiz bilgisinin "
            "bulunamadığı belirtilir."
        ),
    },
    {
        "soru": "Evrak Türü ne demek?",
        "cevap": (
            "Belgenin dilekçe, resmî yazı, bilgi talebi gibi hangi belge sınıfına "
            "ait olduğuna ilişkin sistem tespitidir."
        ),
    },
    {
        "soru": "İşlem Niyeti ne demek?",
        "cevap": (
            "Evrakta talep edilen temel işlemi veya başvurunun amacını gösterir. "
            "Bu bilgi evrakın içeriğinden çıkarılır."
        ),
    },
    {
        "soru": "Belge ID nedir?",
        "cevap": (
            "Belge ID, yüklenen evrakı ve ona bağlı analiz kaydını ayırt etmek için "
            "kullanılan sistem kimliğidir."
        ),
    },
    {
        "soru": "Kısa Özet nedir?",
        "cevap": (
            "Evrakın konusu ve temel talebinin hızlıca anlaşılması için hazırlanan "
            "kısa açıklamadır; karar vermeden önce asıl evrakı da inceleyin."
        ),
    },
    {
        "soru": "Çıkarılan Bilgiler bölümünde ne var?",
        "cevap": (
            "Evrakta bulunan kişi, iletişim, tarih, sayı, konu, talep ve benzeri "
            "alanlar burada listelenir. Bulunamayan bir alan 'Belirtilmemiş' olarak "
            "gösterilebilir."
        ),
    },
    {
        "soru": "Format durumu nedir?",
        "cevap": (
            "Resmî Yazışma Kontrolü bölümünde taslağın biçim kurallarına uygunluğu "
            "gösterilir. Durum Uygun, Kontrol Gerekli veya Hata Tespit Edildi "
            "olabilir; varsa sorunlu alanlar altında listelenir."
        ),
    },
    {
        "soru": "Güven skoru veya güven oranı ne demek?",
        "cevap": (
            "Birim Yönlendirme kararının ne kadar güvenle üretildiğini gösterir. "
            "Arayüz bu değeri yüzde olarak sunar; düşük değer sonucu daha dikkatli "
            "incelemeniz gerektiği anlamına gelir."
        ),
    },
    {
        "soru": "Önerilen birim ne anlama geliyor?",
        "cevap": (
            "Sistem, evrakın içeriğine göre hangi birimin ilgilenmesi gerektiğini "
            "Birim Yönlendirme bölümünde önerir. Bu bir öneridir, kesin karar değildir."
        ),
    },
    {
        "soru": "Yönlendirme gerekçesi nedir?",
        "cevap": (
            "Birim Yönlendirme bölümündeki Gerekçe alanı, evrakın neden önerilen "
            "birime yönlendirildiğini açıklar."
        ),
    },
    {
        "soru": "Eksik bilgi tespiti nasıl çalışır?",
        "cevap": (
            "Sistem, evrakta olması beklenen ama bulunmayan bilgileri (örneğin tarih, "
            "imza veya adres) otomatik olarak işaretler. Eksik yoksa 'Belgede zorunlu "
            "eksik bilgi tespit edilmedi.' mesajı gösterilir."
        ),
    },
    {
        "soru": "Personel incelemesi gerekli ne demek?",
        "cevap": (
            "Eksik veya belirsiz bilgi bulunduğu için sonucun yetkili personel "
            "tarafından kontrol edilmesi gerektiğini belirtir."
        ),
    },
    {
        "soru": "Mevzuat veya hukuki analiz bölümünde ne görüyorum?",
        "cevap": (
            "İlgili Mevzuat bölümünde evrakla eşleşen kanun veya yönetmelik, madde "
            "bilgisi, metin ve eşleşme oranı gösterilir. Doğrulanmış eşleşme yoksa "
            "bu durum açıkça belirtilir."
        ),
    },
    {
        "soru": "Mevzuat eşleşme oranı ne demek?",
        "cevap": (
            "İlgili Mevzuat kartındaki Eşleşme yüzdesi, bulunan kaynağın evrakla "
            "benzerlik düzeyini gösterir. Kaynak metnini incelemek için 'Devamını Gör', "
            "kısaltmak için 'Daralt' düğmesini kullanabilirsiniz."
        ),
    },
    {
        "soru": "Taslak nedir, nasıl kullanılır?",
        "cevap": (
            "Resmî Yazı Taslağı, sistemin hazırladığı resmî yazı önerisidir. Resmî "
            "Görünüm ve Ham Taslak sekmelerinden inceleyin; nihai işlem öncesinde "
            "personel kontrolünü tamamlayın."
        ),
    },
    {
        "soru": "Taslak Türü ne demek?",
        "cevap": (
            "Üretilen metnin Cevap Yazısı, Üst Yazı, Bilgilendirme Metni veya Eksik "
            "Bilgi Talebi gibi hangi resmî yazı türünde hazırlandığını gösterir."
        ),
    },
    {
        "soru": "Resmî Görünüm ve Ham Taslak arasındaki fark nedir?",
        "cevap": (
            "Resmî Görünüm taslağın düzenlenmiş belge görünümünü, Ham Taslak ise "
            "üretilen düz metni gösterir. Ham Taslak alanı bu ekranda salt okunurdur."
        ),
    },
    {
        "soru": "Taslağı nasıl indiririm?",
        "cevap": (
            "Resmî Yazı Taslağı panelindeki 'DOCX' düğmesine tıklayın. Düğmenin "
            "üzerine gelindiğinde 'DOCX olarak indir' açıklaması görünür ve biçim "
            "kurallarına uygun belge indirilir."
        ),
    },
    {
        "soru": "Belgedeki QR kod ne işe yarar?",
        "cevap": (
            "QR kod, belgenin sistemde hangi analiz sonucuna dayandığını gösteren "
            "bir doğrulama kodudur."
        ),
    },
    {
        "soru": "Öncelik veya aciliyet nasıl belirleniyor?",
        "cevap": (
            "Evraktaki açık aciliyet ifadeleri ve son tarih bilgisi bugünün tarihiyle "
            "karşılaştırılarak kural tabanlı hesaplanır. Bu bir yapay zekâ tahmini "
            "değil, sabit bir hesaplamadır."
        ),
    },
    {
        "soru": "Onayla ve Reddet ne yapar?",
        "cevap": (
            "Onayla, personel incelemesindeki sonucu kabul eder. Reddet, ret "
            "gerekçesi alanını açar; gerekçeyi yazıp yeniden Reddet düğmesine "
            "bastığınızda sonuç reddedilir. İptal, ret formunu kapatır."
        ),
    },
    {
        "soru": "Personel Onayı Gerekiyor bölümü neden çıkıyor?",
        "cevap": (
            "Analiz veya taslak insan kararı gerektirdiğinde bu bölüm gösterilir. "
            "Personel sonucu inceleyip Onayla veya Reddet işlemini seçer."
        ),
    },
    {
        "soru": "Sistem bir konuda emin değilse ne olur?",
        "cevap": (
            "Güven düşükse veya eksik ya da belirsiz bilgi varsa sistem personel "
            "incelemesi gerektiğini belirtir; nihai kararı otomatik olarak vermez."
        ),
    },
    {
        "soru": "Sistem yanlış bir şey söylediyse ne yapmalıyım?",
        "cevap": (
            "Evrakı, çıkarılan bilgileri, mevzuat kaynağını ve gerekçeleri karşılaştırın. "
            "Sonuç uygun değilse Personel Onayı Gerekiyor bölümündeki Reddet işlemini "
            "kullanıp gerekçeyi yazın."
        ),
    },
    {
        "soru": "Aynı vatandaşın önceki evrakını nasıl görürüm?",
        "cevap": (
            "Mevcut analiz ekranında önceki başvuruları listeleyen bir İlgili Evrak "
            "bölümü bulunmuyor. Kurumunuzdaki yetkili kayıt sistemi üzerinden kontrol "
            "edin."
        ),
    },
    {
        "soru": "Başka bir kurum profiliyle nasıl çalışırım?",
        "cevap": (
            "Mevcut ekranda kurum profili seçimi bulunmuyor. Kurum değiştirme işlemi "
            "bu arayüz sürümünden yapılamaz."
        ),
    },
    {
        "soru": "Yönetici paneli veya istatistikler nerede?",
        "cevap": (
            "Mevcut ekranda ayrı bir Yönetici Paneli veya İstatistikler sekmesi "
            "bulunmuyor."
        ),
    },
    {
        "soru": "Sistem hangi mevzuatı biliyor?",
        "cevap": (
            "Sistem, resmî yazışma yönetmeliği ve kılavuzu dahil olmak üzere yirmiyi "
            "aşkın kanun ve yönetmeliği kapsayan bir mevzuat veritabanına sahiptir."
        ),
    },
    {
        "soru": "Chatbot'a mevzuatla ilgili soru sorabilir miyim?",
        "cevap": (
            "Evet. Kanun numarasını veya maddeyi açıkça belirterek sorabilirsiniz; "
            "mevzuat modu ilgili kaynağı kullanarak kaynaklı yanıt vermek üzere "
            "tasarlanmıştır."
        ),
    },
    {
        "soru": "Chatbot'a taslağı değiştirmesini söyleyebilir miyim?",
        "cevap": (
            "Taslak düzenleme modu değişiklik önermek üzere tasarlanmıştır. Öneri "
            "uygulanmadan önce resmî yazı kurallarına uygunluk kontrolünden geçer; "
            "uygun olmayan değişiklik uygulanmaz."
        ),
    },
    {
        "soru": "Sistem internete veya dışarıya veri gönderiyor mu?",
        "cevap": (
            "Sistem, kurum onaylı altyapı üzerinde çalışır; veriler yetkisiz üçüncü "
            "taraflarla paylaşılmaz."
        ),
    },
    {
        "soru": "Bir hata mesajı aldım, ne yapmalıyım?",
        "cevap": (
            "Sayfayı yenileyip tekrar deneyin. Üst bölümde API ve diğer servis "
            "durumlarını kontrol edin. Sorun devam ederse teknik ekibe bildirin."
        ),
    },
    {
        "soru": "Analiz ne kadar sürer?",
        "cevap": (
            "Evrakın uzunluğuna göre değişir; genellikle birkaç saniye ile bir dakika "
            "arasında tamamlanır. Süreç göstergesi tamamlanan aşamaların sürelerini "
            "saniye cinsinden gösterir."
        ),
    },
    {
        "soru": "Bu chatbot'un sınırları neler?",
        "cevap": (
            "Chatbot bu sistemin kullanımı, mevzuat soruları ve desteklenen taslak "
            "işlemleri için tasarlanmıştır; genel sohbet veya sistem dışı konularda "
            "yardımcı olamaz. Nihai karar ve doğrulama her zaman personeldedir."
        ),
    },
]


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.casefold().replace("i̇", "i")
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def match_faq(user_message: str, esik: int = ESLESME_ESIGI) -> str:
    """En yakın SSS yanıtını veya her durumda güvenli fallback metnini döndürür."""

    normalized_message = _normalize_text(user_message)
    if not normalized_message:
        return FALLBACK_MESAJI

    best_faq: dict[str, str] | None = None
    best_score = -1.0

    for faq in SSS_LISTESI:
        score = fuzz.partial_ratio(normalized_message, _normalize_text(faq["soru"]))
        if score > best_score:
            best_score = score
            best_faq = faq

    if best_faq is not None and best_score >= esik:
        return best_faq["cevap"]
    return FALLBACK_MESAJI


def is_mevzuat_sorusu(message: str) -> bool:
    """Mesajın açık bir mevzuat anahtar sözcüğü içerip içermediğini belirler."""

    return bool(MEVZUAT_SORUSU_RE.search(_normalize_text(message)))


@lru_cache(maxsize=1)
def _get_legal_agent() -> "LegalAgent":
    """Ağır RAG bağımlılıklarını ilk mevzuat sorusuna kadar yüklemez."""

    from backend.app.agents.legal_agent import LegalAgent

    return LegalAgent()


def handle_legal_question(message: str) -> str:
    """Mevzuat sorusunu mevcut LegalAgent'a iletip kaynaklı yanıtı biçimler."""

    try:
        result = _get_legal_agent().analyze(query=message)
    except Exception:
        return MEVZUAT_SERVIS_HATASI_MESAJI

    answer = str(result.get("answer") or "").strip()
    evidence = result.get("evidence") or []

    if not evidence:
        return answer or MEVZUAT_KANIT_BULUNAMADI_MESAJI

    if not answer:
        return MEVZUAT_KANIT_BULUNAMADI_MESAJI

    try:
        score = float(result.get("retrieval_score"))
    except (TypeError, ValueError):
        return answer

    score = min(max(score, 0.0), 1.0)
    score_text = f"{score * 100:.1f}".replace(".", ",")
    return (
        f"{answer}\n\n"
        f"Kaynak eşleşme skoru: %{score_text}\n"
        "Not: Bu değer hukuki doğruluk olasılığı değil, mevzuat arama "
        "benzerlik skorudur."
    )


def handle_chat_message(message: str) -> str:
    """Mod B mevzuat yönlendirmesini, aksi durumda Mod A SSS'yi çalıştırır."""

    if is_mevzuat_sorusu(message):
        return handle_legal_question(message)
    return match_faq(message)


__all__ = [
    "ESLESME_ESIGI",
    "FALLBACK_MESAJI",
    "MEVZUAT_KANIT_BULUNAMADI_MESAJI",
    "MEVZUAT_SERVIS_HATASI_MESAJI",
    "SSS_LISTESI",
    "handle_chat_message",
    "handle_legal_question",
    "is_mevzuat_sorusu",
    "match_faq",
]
