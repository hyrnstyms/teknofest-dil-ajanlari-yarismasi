# KAMUAI FINAL AGENT REFACTOR - FAZ 2 RAPORU

**Tarih:** 2026-08-27
**Kapsam:** Extraction Optimizasyonu, Profile-Driven Requirements ve Uncertainty Yönetimi

## 1. Zero-Call Optimization (ExtractionAgent)
Faz 2 kapsamında `ExtractionAgent` içerisinde deterministik (heuristic) yollarla tamamen çözülebilen evraklarda **LLM çağrısını sıfıra indiren (Zero-Call)** optimizasyon uygulandı. 
- Semantik çıkarma adımı öncesinde hedef alanlar (`target_semantic`) kontrol edilmekte, liste boşsa `_extract_with_llm` fonksiyonu **asla çalıştırılmamaktadır**.
- `other_entities` alanı sadece başka bir alan için zorunlu LLM çağrısı yapılıyorsa opsiyonel olarak listeye eklenmektedir, tek başına LLM çağrısını tetiklememektedir.

## 2. Semantik Doğrulama (Field-Aware Validation)
LLM tarafından üretilen semantik alanlar `_validate_semantic_field` ile alan bazında denetlenmektedir:
- `person_name`: "Bakanlığı", "Belediye Başkanlığı", "Makamına", "Sayın" vb. ifadeler taşıyan değerler `INVALID` kabul edilerek hatalı entity çıkarımı engellendi.
- `address`: Hedef kuruma hitap içeren bariz hatalı adresler (örn. "... Kaymakamlığına") `INVALID` kabul edildi.
- `recipient`: Gönderen antetinin hatalı yakalanması için korumalar eklendi.

`INVALID` olarak değerlendirilen alanlar çıkartılmış sayılmamakta ve Missing/Uncertain sürecine aktarılmaktadır.

## 3. Strict Signature ve Authority Semantics
Daha önce sadece "imza" veya "vekaletname" kelimesi geçmesiyle yetinilen alanlarda sıkılaştırma yapıldı:
- **Missing:** Açıkça "imzasızdır", "imza bulunmamaktadır" veya "vekaletname yoktur" durumları.
- **Present:** "Elektronik olarak imzalanmıştır", "güvenli elektronik imza", "vekaletname ekte sunulmuştur" gibi güçlü kanıtlar.
- **Unknown:** Yalnızca "imza" veya zayıf emareler geçen, durumu kesin olmayan haller.

## 4. Missing vs Uncertain Ayrımı (MissingFieldAgent)
Extraction aşamasından "unknown" statüsüyle gelen alanlar (`signature_present` dahil olmak üzere) veya hiç tespit edilemeyen kritik fiziksel alanlar (imza vb.) doğrudan `uncertain_fields` dizisine atılmaktadır. 
"Alan bulunamadı" varsayımı otomatik olarak `missing` yapılmamaktadır. Belirsiz olan bu alanlar `needs_human_review = True` işaretini tetikler.

## 5. Profile-Driven Requirements
`MissingFieldAgent` artık zorunlu form alanlarını (`required_fields`) **Institution Profile (YAML)** üzerinden okumaktadır.
- Çözümleme sırası: `Institution Profile (document_subtype)` -> `Institution Profile (document_type)` -> `Legacy Fallback (REQUIREMENT_RULES)` şeklindedir.
- YAML tarafında Kaymakamlık ve Belediye profillerindeki `evrak_turleri` bloklarına `required_fields` eklendi (Örn: bilgi_edinme -> person_name, address, signature_present, request).
- Bu sayede koda müdahale etmeden YAML profilini güncelleyerek kuruma ve belge alt türüne özel requirement'lar tanımlanabilir hale gelmiştir.

## Sonuç
Test suitine eklenen `test_extraction_performance.py` ile bu optimizasyonlar teyit edilmiş ve uygulanan sıkı kurallara uygun olarak tüm Regresyon Testleri başarıyla geçmiştir.
