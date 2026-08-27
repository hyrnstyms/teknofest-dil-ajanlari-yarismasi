# KAMUAI FINAL AGENT REFACTOR - FAZ 6
**Aşama:** CHAT BOUNDARIES + OPTIONAL TRANSFER + STATE CLEANUP

## 1. ChatAgent Sınırlarının Netleştirilmesi
ChatAgent, evrak analiz işlemlerini tekrarlamayacak, kullanıcı sorularına daha dar kapsamlı (ve güvenli) cevaplar verecek şekilde güncellendi.
- **Router Güncellemesi:** Kullanıcıdan gelen soruları sınıflamak üzere router prompt'u güncellendi. `A` (Aktif Belge Sorusu) ve `X` (Kapsam Dışı) etiketleri destekleniyor.
- **ChatDocumentContext Entegrasyonu:** ChatAgent, ana evrak analiz state'ine tam bağımlı olmak yerine daraltılmış `ChatDocumentContext` üzerinden çalışacak şekilde güncellendi.
- **Yeniden Analiz Engellendi:** Aktif belge soruları (`A`) doğrudan mevcut `ChatDocumentContext` kullanılarak cevaplanır, tekrar DocumentAgent veya ExtractionAgent tetiklenmez.
- **Mevzuat Soruları Grounding:** Mevzuat soruları (label `M`) `LegalAgent`'a iletilir ve RAG (Retrieval-Augmented Generation) altyapısı ile kanıt destekli olarak cevaplandırılır.
- **Taslak (Draft) Düzenleme Fact Koruması:** Taslak düzenlemede ChatAgent'ın yeni kişi/kurum/kanıt uydurmasını engelleyecek kesin prompt kuralları getirildi.
- **Enum Sızıntısının Engellenmesi:** Backend'de kullanılan `basvuru`, `dilekce`, `signature_present` gibi enum tipleri kullanıcı arayüzüne sunulurken `FIELD_LABELS` ve `type_labels` aracılığıyla Türkçeleştirilmiş isimleri (örn. "Başvuru", "İmza") ile gösterilir.

## 2. TransferAgent (Kurumlar Arası Transfer)
- `TransferAgent`, zorunlu bir iş akışı adımı olmak yerine kurumlar arası aktarımı öneren (recommendation) bir özellik olarak yapılandırıldı.
- Çıktı formatına `capability_type = "recommendation"` alanı eklendi.
- Hedef kurum profili eksik olduğunda `needs_human_review = True` yapılarak personel incelemesi zorunlu kılındı.
- `transfer_required` alanı, bir işlemin gerçekleştiğini ifade etmek yerine personelin alması gereken karara bir "öneri" niteliğinde tasarlandı.

## 3. State Cleanup (Durum Temizliği)
- `state.py` içerisinde tanımlanan evrak state hiyerarşisi (document, routing, extraction vs.) temizlendi ve duplicate veriler ayıklandı.
- Eski (Legacy) alanlara uyumluluk katmanı (compatibility adapter) oluşturuldu. API response üzerinde `@property` veya yardımcı bir adaptör ile geriye dönük uyumluluk (backward compatibility) korundu ve çift yazımın (duplicate write) önüne geçildi.

## 4. Testler ve Regresyon
- ChatAgent testleri güncellenerek kapsam dışı (`X` -> `out_of_domain`), taslak, mevzuat ve belirsiz alanların doğru isimlendirmeleri (örn. "Adres") kontrol edildi.
- Genel regresyon testleri `pytest` üzerinden çalıştırılarak doğrulandı.

## 5. Sonuç
Phase 6 başarıyla tamamlanmış olup evrak işleme süreçlerinin etrafındaki modüller (Chat ve Transfer) optimize edilmiş, durum (state) yapısındaki kalıntılar (legacy fields) temizlenmiştir.
