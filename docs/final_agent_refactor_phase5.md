# KamuAI Final Agent Refactor - Phase 5
**Writing Agent Contract + Safe Official Drafting**

## Amaç ve Kapsam
Bu fazda `WritingAgent` bileşeninin yetki sınırları daraltılmış, taslak metin (draft) oluşturma karar mekanizmaları tamamen kural tabanlı (deterministik) hale getirilmiş ve resmi metin üretimi sırasındaki uydurma (hallucination) riski minimuma indirilmiştir.

### Yapılan Temel Değişiklikler

1. **WritingContext Yapısı**
   - Eski ve dağınık parametreler yerine `WritingContext` (TypedDict) sözleşmesi oluşturuldu.
   - `WritingAgent.draft` metodu artık `context: WritingContext` parametresini birincil giriş olarak alıyor.
   - Geriye dönük uyumluluk için eski `kwargs` ile çağrımlar dahili bir adaptör aracılığıyla `WritingContext` yapısına dönüştürülüyor.

2. **Deterministik Draft Type Kararı**
   - Taslak türü seçimi için (draft type) gerçekleştirilen LLM çağrısı tamamen kaldırıldı.
   - Karar ağacı `_decide_draft_type` içerisine taşındı:
     - Eksik bilgi (missing field) varlığında -> `eksik_bilgi_talebi`
     - İşlem amacı (`process_intent`) belirginse -> Map üzerinden eşleştirme (`basvuru` -> `cevap_yazisi`, `sevk` -> `ust_yazi`, `bildirim` -> `bilgilendirme_metni` vb.)
     - Kapsamlı iç transfer/sevk routing kuralları -> `ust_yazi`
     - Hiçbiri değilse (belirsizlik) -> `diger` (human review ile bloklanmış durumda)

3. **Güvenli Fakt Çıkarımı (Verified Facts vs Workflow Metadata)**
   - `workflow.py` tarafında `WritingContext` içerisindeki `verified_facts` listesi raw sistem/enum (ör. `basvuru`, `ust_yazi`) etiketlerini içermeden oluşturuldu.
   - Sadece `"validated": True` ve `value`'su mevcut olan alanlar temiz Türkçe etiketlerle ("Başvuru Sahibi: ...", "Belge Sayısı: ...") aktarıldı.

4. **Kritik Belirsizliklerin Yönetimi (Uncertainty)**
   - Belirsiz (uncertain) alanlar içeriksel ve süreçsel olarak ikiye ayrıldı.
   - Gönderen (sender) veya muhatap (recipient) gibi hayati konulardaki belirsizlik, hatalı metin oluşturmayı önlemek adına üretimi bloke eder (`blocked_uncertain_fields`).
   - Sadece imza veya yetki belgesi yokluğu, içeriği bozmayacağından engel teşkil etmez, üretilir ancak `requires_human_approval` işareti koyulur.

5. **Prompt Katılaştırma ve RAG İzolasyonu**
   - LLM generation komutları sertleştirildi; geliştirici-enum kelimeleri ("basvuru", "diger") metne (body/subject) sızmayacak şekilde sansürlendi.
   - Doğrulanmamış eylemler için ("kabul edilmiştir", "onaylanmıştır", vb.) sahte (hallucinated) kararlar üretilmesi engellendi.
   - Resmi yazışma bağlamı (RAG), yalnızca biçimsel referans olarak kullanılarak, hukuki veya olgusal fakt uydurmaya kalkan model eğilimi bastırıldı.

6. **Tamir Modülü (Repair Bound)**
   - Draft onarımında (`_repair_draft`) potansiyel döngü (infinite loop) riskini gidermek için en fazla 1 kez çağrılabilecek şekilde kontrol güvenceye alındı.

## Testler ve Regresyon (Regression)
- `test_writing_agent.py` sıfırdan yazılarak 23 ayrı senaryo için testler dahil edildi.
- Test kapsamı: "happy-path" vatandaş dilekçesi, iç sevk (kurum transferi), eksik alan tespiti (deterministic eksik bilgi), LLM çağrı sınırları (mock kontrolleri), format ve RAG yetersizlikleri gibi konuları içerir.
- Ayrıca `test_context_renderer_integration.py` ve `test_workflow.py` entegrasyon testleri yeni Pydantic/TypedDict şemalarıyla güncellenerek tam bir backend regresyonu yapılmıştır ve LLM çağrı limitleri 1 (Generation) veya en fazla 2 (Generation + Repair) ile sınırlanmıştır.

## Sonraki Adımlara Hazırlık (Faz 6)
Bu faz ile birlikte `WritingAgent` üzerindeki olası kırılganlıklar sıfırlanmıştır. Sistem bütününde kurum konteksti ve katı sözleşmeli bileşen entegrasyonu başarılıdır. Sonraki aşamada "Telemetry & Guardrails" ya da deployment senaryolarına problemsiz geçiş yapılabilir.
