# KAMUAI FINAL AGENT REFACTOR — FAZ 4 RAPORU

## 1. Institution Propagation
**Önceki Durum**: `KamuaiWorkflow` içinde `RoutingAgent`, verilen kurum (`institution`) parametresi ile oluşturulurken `QualityAgent` varsayılan olarak `kaymakamlik` profiliyle başlatılıyordu. Bu durum, "belediye" workflow'larında quality gate'in geçerli kurum birimlerini bulamamasına ve gereksiz "invalid unit" hataları üretmesine neden oluyordu.
**Sonraki Durum**: `KamuaiWorkflow` başlatılırken kullanılan `institution` parametresi tüm bağımlı agentlara (özellikle `QualityAgent`'a) dağıtıldı. Artık tüm workflow boyunca tek bir aktif kurum context'i (Single Source of Truth) kullanılmaktadır.

## 2. Routing Sinyalleri ve Subtype Routing
**Yenilikler**:
- Faz 1'de oluşturulan `document_subtype`, kural tabanlı (rule-based) `RoutingAgent`'a eklendi.
- `route()` signature'ına opsiyonel `document_subtype` parametresi eklendi.
- Routing profili eşleşmelerinde (`doc_type_mapping`) artık **öncelikle** `document_subtype` sinyali değerlendiriliyor. Eğer profilde bir karşılığı bulunmazsa (veya subtype gelmemişse) `document_type` kullanılıyor (Broad Fallback).
- `score_breakdown` çıktısı `subtype_score` içerecek şekilde genişletildi.

## 3. Generic Keywords & Ambiguity Stratejisi
- "ruhsat", "şikayet", "yardım" gibi tek kelimelik anahtar kelimelerin (generic keywords) yüksek skor üretip yanlış birimleri seçmemesi için, RoutingAgent'taki margin kontrolü (< 15 threshold) güçlendirildi.
- Minimum `30` güven skoru barajı korundu. Sadece generic keyword'ten gelen `20` puan barajı geçemediği için sistem otomatik olarak `needs_human_review = True` (manuel kontrol) ve `recommended_unit = None` döndürmektedir.
- **Why No Routing LLM**: Halihazırdaki deterministik yapı (profil kuralları + exemplar eşleşmeleri + açık/explicit hedef kontrolü + ambiguity tespit mantığı) yönlendirme işlemi için güvenli ve LLM halüsinasyonu riskinden uzak (Zero-Call) çalışmaktadır. Belirsizlik durumlarında LLM ile "tahmin" yürütmek yerine, manuel incelemeye yönlendirmek tercih edilmiştir.

## 4. Quality Status ve Decision Semantics
`QualityAgent` artık sadece `pass`, `warning`, `fail` statülerini üretmekle kalmıyor, aynı zamanda açık bir **decision** sinyali veriyor:
- **`continue`**: Hiçbir sorun yok (`status = pass` ve `requires_human_review = False`).
- **`human_review`**: Güvenli ancak manuel kontrol gerektiren belirsizlikler (ör. Ambiguous routing, critical extraction fields like signature missing/uncertain, vb.)
- **`block`**: İşlemin güvenli bir şekilde sonlanmasını engelleyen çelişkiler (ör. Extraction present vs missing/uncertain çelişkisi, unverified outcome claims "onaylanmıştır", profil dışında bir hedefe yönlendirme hatası).

## 5. Active Institution Validation & İzolasyon
Yönlendirilen (`recommended_unit`) birimin "aktif kurumun" registry (YAML profil) valid_units listesinde olup olmadığı kesin olarak test edildi.
"Belediye" profiline sahip bir workflow'da üretilen geçerli bir Belediye biriminin (ör. Zabıta Müdürlüğü) "Kaymakamlık" profiline takılarak fail vermediği kanıtlandı.

## 6. Testler
- Hedeflenen unit testleri: `test_routing_agent.py` ve `test_quality_agent.py`.
- Subtype eşleşmesi (imar_talebi -> İmar ve Şehircilik), margin testleri, belediye izolasyon testi başarıyla tamamlandı.
- Tüm `backend/tests` regression (454 test) `pytest` ile PASS durumundadır.

## 7. Changed Files
- `backend/app/graph/workflow.py`
- `backend/app/agents/routing_agent.py`
- `backend/app/agents/quality_agent.py`
- `backend/tests/test_routing_agent.py`
- `backend/tests/test_quality_agent.py`

## 8. Faz 5 İçin Prerequisites (WritingAgent Refactor)
- Taxonomy (`document_subtype`), güvenilir kural yönlendirmesi (`RoutingAgent`) ve deterministik validation kapısı (`QualityAgent`) hazır durumdadır.
- Bir sonraki Faz 5'te, `WritingAgent`'ın şablon-bazlı (template-driven) yapısına geçişi sırasında QualityAgent'ın ürettiği `block` kararları ve official format kontrolleri doğrudan temel alınacaktır.
