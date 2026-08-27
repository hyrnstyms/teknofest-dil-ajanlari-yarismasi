# Faz 1 Raporu: Document Taxonomy & Institution-Aware Contract

## Özet
Faz 1 kapsamında KAMUAI evrak sınıflandırma sistemi `document_type` (genel/yapısal) ve yeni eklenen `document_subtype` (kurum spesifik) olarak iki aşamalı bir hiyerarşiye geçirilmiştir. Sistemin mevcut dış entegrasyonlarını (API consumers vs.) bozmamak adına `document_type` sözleşmesi korunmuş, `document_subtype` alanı geriye dönük uyumlu (backwards-compatible) bir şekilde sisteme dahil edilmiştir. 

## Taxonomy Contract

### Eski Taxonomy (Phase 0)
- `document_type`: Hem genel belge tipini (dilekçe, vb.) hem de spesifik türleri (bilgi_edinme, vb.) aynı enum listesinde zorlayan, kurum profillerinden bağımsız hardcoded yapı.
- `process_intent`: İşlem amacı (bilgi talebi, vb.).

### Yeni Taxonomy (Phase 1)
- `document_type`: Genel/yapısal tür (dilekce, resmi_yazi, form, vb.). Sözleşme değişmedi.
- `document_subtype`: **YENİ.** Aktif kurum profilinde (`kurum_profili_<isim>.yaml`) yer alan `evrak_turleri` alanından dinamik olarak türetilir (örn. `bilgi_edinme`, `ihale_itirazi`). Eğer kurum profili yoksa veya LLM güvenilir bir eşleşme bulamazsa `null` döner.
- `process_intent`: İşlem amacı. Sözleşme değişmedi.

## Değişiklikler ve Implementasyon Stratejisi

### 1. DocumentAgent (Subtype Sınıflandırma ve Validation)
- Constructor'a `institution_profile` parametresi eklendi.
- Mevcut tek LLM çağrısı (`_classify_with_llm`) genişletilerek kurum profilindeki `evrak_turleri` prompt içine eklendi. Modelden SADECE aktif profil içindeki allowed subtype'lardan birini seçmesi, uymuyorsa veya kurum profili `None` ise `null` döndürmesi istendi.
- `_validate_subtype` metodu ile modelin döndürdüğü sonuç Python tarafında kontrol edildi. Allowed-list dışı hiçbir sonuca (fuzzy matching vb.) tolerans gösterilmedi ve bu gibi durumlarda subtype `None` olarak düzeltildi.
- `_normalize_llm_result` güncellenerek küçük model fallback vs. sırasında `document_subtype` alanının kaybolması önlendi.
- Evidence mekanizmasında `field: "document_subtype"` desteklendi.

### 2. KamuaiWorkflow (Profile Injection)
- `KamuaiWorkflow.__init__` içinde `load_institution_profile` ile (varsayılan "kaymakamlik") kurum profili yüklendi.
- Yüklenen profil `DocumentAgent` örneğine inject edildi.
- `node_missing_field` adımında, `state.document`'ten elde edilen `document_subtype` verisi `MissingFieldAgent`'a parametre olarak aktarıldı.

### 3. MissingFieldAgent (Precedence and Lookup Order)
Mevcut `REQUIREMENT_RULES`'i bozmadan, `document_subtype` bilgisi geldiğinde öncelikle subtype'a göre kontrol yapılması sağlandı:
1. `(document_subtype, process_intent)`
2. `(document_subtype, "*")`
3. `(document_type, process_intent)`
4. `(document_type, "*")`
5. `("*", "*")`

### 4. Testler ve Regresyon (Backend)
Yeni yazılan test modülü: `backend/tests/test_document_subtype.py` (Mock LLM ile)

Aşağıdaki **12 senaryo** sorunsuz olarak geçmektedir:
1. Kaymakamlık - bilgi edinme (Valid eşleşme)
2. Kaymakamlık - sosyal yardım başvurusu (Valid eşleşme)
3. Kaymakamlık - ihale itirazı (Valid eşleşme)
4. Belediye - ruhsat başvurusu (Valid eşleşme)
5. Belediye - imar talebi (Valid eşleşme)
6. Belediye - şikâyet (Valid eşleşme)
7. Belge hiçbir profile subtype'a uymuyor (`subtype = None`)
8. LLM profile dışı subtype döndürüyor (Validation failure -> `None`)
9. Institution profile None (Geriye dönük uyumluluk, `subtype = None`, `needs_human_review = False` valid eşleşmeler için)
10. Empty document (Fallback -> `diger`)
11. MissingFieldAgent subtype precedence (SubType requirement önceliği test edildi)
12. Existing callers backward compatibility (`document_subtype` parametresi yollanmadığında sistemin hala standart `document_type` olarak fallback atması)

Regresyon: `backend/tests/test_institutions.py`, `backend/tests/test_routing_agent.py`, `backend/tests/test_missing_fields.py`, `backend/tests/test_priority_agent.py` dahil **59 test başarıyla tamamlandı.**

## Kalan İşler (Faz 2 Hazırlığı)
- `MissingFieldAgent` şu an için halen hardcoded `REQUIREMENT_RULES` listesine bakıyor. Faz 2'de kurum profili bazlı kural yapısı doğrudan YAML'dan okunacak.
- `RoutingAgent` ve diğer modüllerin `document_subtype` tabanlı akış yönlendirmelerine tam geçişi sağlanacak.
