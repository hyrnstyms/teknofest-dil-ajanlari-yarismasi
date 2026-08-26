# KAMUAI Agent Zinciri Audit Raporu

## Yürütme özeti

Bu rapor kod ve RAG/embedding dosyaları değiştirilmeden, `SENT-0171` örneği ile gerçek EVREN ve canlı retrieval kullanılarak güncellenmiştir. Çalışma sırası şöyledir:

```text
DocumentAgent -> ExtractionAgent -> LegalAgent -> MissingFieldAgent -> SummaryAgent -> RoutingAgent -> WritingAgent -> QualityAgent -> HumanReview
```

Seçili kayıt orta zorluktadır, `4734 sayılı Kamu İhale Kanunu` atfı içerir ve veri seti tarihi eksik gösterir.

```text
ÖRENLİ İLÇE KAYMAKAMLIĞINA

BAŞVURAN: Polat Madencilik adına Pelin Sönmez

KONU: Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi

AÇIKLAMALAR:
1. Kurum araçları akaryakıt alımı ihalesinin idari şartnamesi ile sözleşme tasarısında ödeme vadelerine ilişkin birbiriyle çelişkili maddeler bulunmaktadır, idari inceleme talep ediyoruz.
2. 4734 sayılı Kamu İhale Kanunu uyarınca gerekli yasal incelemenin yapılmasını talep ediyoruz.
3. Gereğinin ivedilikle yapılmasını arz ederim.

İmza: Polat Madencilik adına Pelin Sönmez
```

Tüm düğümler tamamlandı. Zamanlamalar:

```json
{
  "document_agent": {
    "duration_ms": 1841,
    "status": "completed"
  },
  "extraction_agent": {
    "duration_ms": 3013,
    "status": "completed"
  },
  "legal_agent": {
    "duration_ms": 4831,
    "status": "completed"
  },
  "missing_field_agent": {
    "duration_ms": 0,
    "status": "completed"
  },
  "summary_agent": {
    "duration_ms": 0,
    "status": "completed"
  },
  "routing_agent": {
    "duration_ms": 11,
    "status": "completed"
  },
  "writing_agent": {
    "duration_ms": 2585,
    "status": "completed"
  },
  "quality_agent": {
    "duration_ms": 0,
    "status": "completed"
  },
  "human_review_agent": {
    "duration_ms": 0,
    "status": "completed"
  }
}
```

## Özel soruların canlı cevapları

1. **WritingAgent resmî cevap mı yazıyor?** `cevap_yazisi` üretti; ancak metin kuruma gönderilecek doğru cevap değildir. Muhatap kurumun kendisi (“Örenli İlçe Kaymakamlığı”) seçilmiş, gövde başvuruyu tekrar anlatmış ve “Başvurunuzun işleme alınmış olduğu bilgilerini rica ederim.” diyerek kurum adına uygun olmayan bir talep cümlesi kurmuştur. Ayrıca resmi önizlemede birim, sayı, tarih, ilgi ve imza placeholder'dır.
2. **RoutingAgent profildeki gerçek birimi mi seçti?** Hayır, kesin bir birim seçemedi (`recommended_unit: null`). Eşit 50 puanla üç profil birimi sıralandı; birinci sıradaki “Yazı İşleri Müdürlüğü” kurum profilinde gerçektir, ancak sonuç belirsiz olduğu için ajan doğru yönlendirme yapmamıştır.
3. **WritingAgent girdisindeki altı alan:** `missing_fields` doğrudan vardır; extraction ve routing dar `state` içinde vardır. `legal_context`, `institution_profile` ve `document_type` yoktur.
4. **LegalAgent kaynakları WritingAgent'e aktarılıyor mu?** Hayır. LegalAgent üç adet 4734 kaynağı getirdi, fakat doğrulanmış evidence `[]` oldu; WritingAgent'in girişinde `legal_analysis`/`legal_context` bulunmamaktadır. WritingAgent kendi ayrı “resmî yazışma” retrieval kaynaklarını kullandı.

## Canlı bulgular

- DocumentAgent `dilekce`/`basvuru` sınıflaması yaptı. Bu, veri setinin `ihale_itirazi` etiketi ile uyuşmaz; MissingFieldAgent bu nedenle ihale itirazına özgü tarih kuralını seçmedi.
- ExtractionAgent, başvuru yapılan kurumu yanlışlıkla `address` olarak çıkardı ve `İmza:` metni olmasına rağmen `signature_present: unknown` bıraktı.
- LegalAgent doğru kanun numaralı kaynakları retrieval ile getirdi fakat LLM `{"items":[]}` döndürdü; doğrulanmış hukuki kanıt oluşmadı.
- MissingFieldAgent'in `missing_fields` listesi boş, `signature_present` ise uncertain. WritingAgent yalnız `missing_fields`i dikkate aldığından eksik/şüpheli imzaya rağmen cevap yazısı oluşturdu.
- SummaryAgent deterministik özet üretti; “idari inceleme talep ediyoruz talep edilmektedir” dil hatası içeriyor.
- RoutingAgent raw metni kullanmayıp `dilekce` türü nedeniyle üç birime aynı 50 puanı verdi; bu nedenle yönlendirme `null` oldu.
- WritingAgent'e legal bağlam, belge türü ve kurum profili verilmedi. LLM yanıtı JSON olarak parse edildi, fakat içerik ve muhatap yönünden hatalıdır.
- QualityAgent insan incelemesi gerektiğini belirtti, fakat bu inceleme otomatik düzeltme sağlamaz.

## Ajan bazında canlı giriş ve çıktı kaydı

### document_agent

**Tam tüketilen giriş:**

```json
{
  "raw_text": "ÖRENLİ İLÇE KAYMAKAMLIĞINA\n\nBAŞVURAN: Polat Madencilik adına Pelin Sönmez\n\nKONU: Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi\n\nAÇIKLAMALAR:\n1. Kurum araçları akaryakıt alımı ihalesinin idari şartnamesi ile sözleşme tasarısında ödeme vadelerine ilişkin birbiriyle çelişkili maddeler bulunmaktadır, idari inceleme talep ediyoruz.\n2. 4734 sayılı Kamu İhale Kanunu uyarınca gerekli yasal incelemenin yapılmasını talep ediyoruz.\n3. Gereğinin ivedilikle yapılmasını arz ederim.\n\nİmza: Polat Madencilik adına Pelin Sönmez"
}
```

**State'e yazılan tam çıktı:**

```json
{
  "document_type": "dilekce",
  "process_intent": "basvuru",
  "subject_excerpt": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
  "request_excerpt": "idari inceleme talep ediyoruz",
  "evidence": [
    {
      "field": "subject",
      "text": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi"
    },
    {
      "field": "request",
      "text": "idari inceleme talep ediyoruz"
    }
  ],
  "classification_mode": "llm",
  "evidence_mode": "llm",
  "needs_human_review": false,
  "priority": "HIGH",
  "priority_rule": "explicit_urgency",
  "priority_reason": "Evrak açık bir acil/ivedi işlem ifadesi içeriyor.",
  "deadline": null,
  "days_remaining": null,
  "decision_source": "rule_based",
  "raw_llm_result": {
    "document_type": "dilekce",
    "process_intent": "basvuru",
    "evidence": [
      {
        "field": "subject",
        "text": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi"
      },
      {
        "field": "request",
        "text": "idari inceleme talep ediyoruz"
      }
    ]
  },
  "llm": {
    "provider": "evren",
    "model": "llm-fast"
  }
}
```
### extraction_agent

**Tam tüketilen giriş:**

```json
{
  "raw_text": "ÖRENLİ İLÇE KAYMAKAMLIĞINA\n\nBAŞVURAN: Polat Madencilik adına Pelin Sönmez\n\nKONU: Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi\n\nAÇIKLAMALAR:\n1. Kurum araçları akaryakıt alımı ihalesinin idari şartnamesi ile sözleşme tasarısında ödeme vadelerine ilişkin birbiriyle çelişkili maddeler bulunmaktadır, idari inceleme talep ediyoruz.\n2. 4734 sayılı Kamu İhale Kanunu uyarınca gerekli yasal incelemenin yapılmasını talep ediyoruz.\n3. Gereğinin ivedilikle yapılmasını arz ederim.\n\nİmza: Polat Madencilik adına Pelin Sönmez",
  "document": {
    "document_type": "dilekce",
    "process_intent": "basvuru",
    "subject_excerpt": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
    "request_excerpt": "idari inceleme talep ediyoruz",
    "evidence": [
      {
        "field": "subject",
        "text": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi"
      },
      {
        "field": "request",
        "text": "idari inceleme talep ediyoruz"
      }
    ],
    "classification_mode": "llm",
    "evidence_mode": "llm",
    "needs_human_review": false,
    "priority": "HIGH",
    "priority_rule": "explicit_urgency",
    "priority_reason": "Evrak açık bir acil/ivedi işlem ifadesi içeriyor.",
    "deadline": null,
    "days_remaining": null,
    "decision_source": "rule_based",
    "raw_llm_result": {
      "document_type": "dilekce",
      "process_intent": "basvuru",
      "evidence": [
        {
          "field": "subject",
          "text": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi"
        },
        {
          "field": "request",
          "text": "idari inceleme talep ediyoruz"
        }
      ]
    },
    "llm": {
      "provider": "evren",
      "model": "llm-fast"
    }
  }
}
```

**State'e yazılan tam çıktı:**

```json
{
  "fields": {
    "signature_present": {
      "value": null,
      "status": "unknown",
      "evidence": null,
      "source": "document",
      "method": "deterministic",
      "validated": true
    },
    "authority_document_present": {
      "value": null,
      "status": "unknown",
      "evidence": null,
      "source": "document",
      "method": "deterministic",
      "validated": true
    },
    "subject": {
      "value": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
      "evidence": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
      "source": "document",
      "method": "document_agent",
      "validated": true
    },
    "request": {
      "value": "idari inceleme talep ediyoruz",
      "evidence": "idari inceleme talep ediyoruz",
      "source": "document",
      "method": "document_agent",
      "validated": true
    },
    "person_name": {
      "value": "Polat Madencilik adına Pelin Sönmez",
      "evidence": "BAŞVURAN: Polat Madencilik adına Pelin Sönmez",
      "source": "document",
      "method": "deterministic",
      "validated": true
    },
    "address": {
      "value": "Örenli İlçe Kaymakamlığı",
      "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA",
      "source": "document",
      "method": "llm",
      "validated": true
    },
    "institution": {
      "value": "Örenli İlçe Kaymakamlığı",
      "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA",
      "source": "document",
      "method": "llm",
      "validated": true
    },
    "sender_unit": {
      "value": "Polat Madencilik",
      "evidence": "Polat Madencilik",
      "source": "document",
      "method": "llm",
      "validated": true
    },
    "recipient": {
      "value": "Örenli İlçe Kaymakamlığı",
      "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA",
      "source": "document",
      "method": "llm",
      "validated": true
    },
    "other_entities": {
      "value": [
        {
          "type": "organization",
          "value": "Polat Madencilik",
          "evidence": "Polat Madencilik"
        },
        {
          "type": "organization",
          "value": "Polat Madencilik",
          "evidence": "Polat Madencilik"
        }
      ],
      "evidence": [
        "Polat Madencilik",
        "Polat Madencilik"
      ],
      "source": "document",
      "method": "llm",
      "validated": true
    }
  },
  "warnings": [],
  "needs_human_review": false,
  "llm": {
    "provider": "evren",
    "model": "llm-fast"
  }
}
```
### legal_agent

**Tam tüketilen giriş:**

```json
{
  "document.process_intent": "basvuru",
  "document.subject_excerpt": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
  "document.request_excerpt": "idari inceleme talep ediyoruz",
  "constructed_query": "basvuru Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi idari inceleme talep ediyoruz"
}
```

**State'e yazılan tam çıktı:**

```json
{
  "answer": "Sağlanan kaynaklarda soruya ilişkin doğrulanabilir bir bilgi çıkarılamadı.",
  "evidence": [],
  "sources": [
    {
      "score": 0.56865597,
      "chunk_id": "0c698c92-161c-500d-9a33-d275292f7c8a",
      "title": "Kamu İhale Kanunu (4734)",
      "text": "Madde 56- (Değişik: 22/11/2008-5812/23 md.) \nİdareye şikayet başvurusunda bulunan veya idarece alınan kararı uygun bulmayan aday, \nistekli veya istekli olabilecekler tarafından 55 inci maddenin dördüncü fıkrasında belirtilen \nhallerde ve sürede, sözleşme imzalanmadan önce itirazen şikayet başvurusunda bulunulabilir. \nİhalenin iptaline ilişkin işlem ve kararlardan, sadece şikayet ve itirazen şikayet üzerine alınanlar \nitirazen şikayete konu edilebilir ve bu kararlara karşı beş gün içinde doğrudan Kuruma başvuruda \nbulunulabilir. \nKurum itirazen şikayet başvurularını başvuru sahibinin iddiaları ile idarenin şikayet \nüzerine aldığı kararda belirlenen hususlar ve itiraz edilen işlemler bakımından eşit muamele \nilkesinin ihlal edilip edilmediği açılarından inceler. İdare tarafından şikayet veya itirazen şikayet \nüzerine alınan ihalenin iptal edilmesi işlemine karşı yapılacak itirazen şikayet başvuruları ise \nidarenin iptal gerekçeleriyle sınırlı incelenir. \nKanunda belirtilen sürelere ve usule uyulmadan sözleşme imzalanmış olması veya itirazen \nşikayet başvurusundan feragat edilmesi itirazen şikayet başvurusunun incelenmesine ve 54 üncü \nmaddede sayılan kararlardan birinin alınmasına engel teşkil etmez. \n \n60 20/11/2008 tarihli ve 5812 sayılı Kanunun 23 üncü maddesiyle bu madde başlığı “Kamu İhale Kurulu \ntarafından inceleme” iken, 5/1/2009 tarihinden geçerli olmak üzere metne işlendiği şekilde \ndeğiştirilmiştir. \n\nKurul tarafından gerekli görülen hallerde tarafların ve ilgililerin dinlenmesine karar \nverilir. Bu durumda, Kurul tarafından tespit edilen tarihte taraflar ve ilgililer dinlenir. \nKurum, itirazen şikayete ilişkin nihai kararını, incelenen ihaleye ilişkin gerekli bilgi ve \nbelgeler ile ihale işlem dosyasının kayıtlara alındığı tarihi izleyen yirmi gün içinde vermek \nzorundadır. Bu süre 21 inci maddenin (b) ve (c) bentlerine göre yapılan ihaleler ile şikayet ve \nitirazen şikayet üzerine alınan ihalenin iptal edilmesi işlemine karşı yapılacak itirazen şikayet \nb",
      "source": "4734",
      "rag_domain": "legal",
      "law_number": "4734",
      "document_id": null,
      "madde_no": "56",
      "article": "56",
      "trusted_source": true,
      "metadata": {
        "rag_eligible": true,
        "law_number": "4734",
        "rag_domain": "legal",
        "madde_no": "56",
        "source": "4734",
        "title": "Kamu İhale Kanunu (4734)",
        "trusted_source": true
      }
    },
    {
      "score": 0.5609256,
      "chunk_id": "1fffd493-df26-5842-910e-81bad6d09500",
      "title": "Kamu İhale Kanunu (4734)",
      "text": "Madde 54- (Değişik: 20/11/2008-5812/21 md.)  \nİhale sürecindeki hukuka aykırı işlem veya eylemler nedeniyle bir hak kaybına veya \nzarara uğradığını veya zarara uğramasının muhtemel olduğunu iddia eden aday veya istekli ile \nistekli olabilecekler, bu Kanunda belirtilen şekil ve usul kurallarına uygun olmak şartıyla şikayet \nve itirazen şikayet başvurusunda bulunabilirler. \nŞikayet ve itirazen şikayet başvuruları, dava açılmadan önce tüketilmesi zorunlu idari \nbaşvuru yollarıdır. \nŞikayet başvuruları idareye, itirazen şikayet başvuruları Kuruma hitaben yazılmış imzalı \ndilekçelerle yapılır.  \nDilekçelerde aşağıdaki hususlara yer verilir: \na) Başvuru sahibinin, varsa vekil ya da temsilcisinin adı, soyadı veya unvanı ve adresi. \nb) İhaleyi yapan idarenin ve ihalenin adı veya ihale kayıt numarası. \nc) Başvuruya konu olan durumun farkına varıldığı veya bildirildiği tarih. \nd) Başvurunun konusu, sebepleri ve dayandığı deliller. \ne) İtirazen şikayet başvurularında idareye yapılan şikayetin ve varsa şikayete ilişkin idare \nkararının bildirim tarihi. \n(Değişik beşinci fıkra:28/1/2021-7263/10 md.) Şikâyet ve itirazen şikâyet başvuru \ndilekçelerinde yer alması gereken diğer bilgiler ile bu dilekçelere eklenmesi gereken belgelere, \nbunların sunuluş şekli ile bu başvuruların elektronik ortamda yapılmasına ilişkin usul ve esasları \nbelirlemeye Kurum yetkilidir.  \nİtirazen şikayette bulunanlardan 53 üncü maddenin (j) bendinin (2) nolu alt bendinde \nbelirtilen bedelin dört katı tutarına kadar başvuru teminatı alınmasına Cumhurbaşkanınca karar \nverilebilir. Başvuru teminatları Kurum hesaplarına yatırılır. Bu teminatlar Kurum gelirleri ile \nilişkilendirilmeksizin ayrı hesaplarda tutulur.58 \n(Mülga yedinci fıkra:28/1/2021-7263/10 md.)  \nAynı kişi tarafından birden fazla ihaleye, birden fazla kişi tarafından ise aynı ihaleye tek \ndilekçe ile başvuruda bulunulamaz. \n(Ek: 6/2/2014-6518/50 md.) Başvuruların ihaleyi yapan idare veya Kurum dışındaki idari \n \n56 20/11/2008 tarihli ve 5812 say",
      "source": "4734",
      "rag_domain": "legal",
      "law_number": "4734",
      "document_id": null,
      "madde_no": "54",
      "article": "54",
      "trusted_source": true,
      "metadata": {
        "rag_eligible": true,
        "law_number": "4734",
        "rag_domain": "legal",
        "madde_no": "54",
        "source": "4734",
        "title": "Kamu İhale Kanunu (4734)",
        "trusted_source": true
      }
    },
    {
      "score": 0.5538851,
      "chunk_id": "213251bd-4eeb-512f-af39-42ed2e69083f",
      "title": "Kamu İhale Kanunu (4734)",
      "text": "Madde 37- İhale komisyonunun talebi üzerine idare tekliflerin incelenmesi, \nkarşılaştırılması ve değerlendirilmesinde yararlanmak üzere net olmayan hususlarla ilgili \nisteklilerden yazılı olarak tekliflerini açıklamalarını isteyebilir. Ancak bu açıklama, hiçbir şekilde \nteklif fiyatında değişiklik yapılması veya ihale dokümanında yer alan şartlara uygun olmayan \ntekliflerin uygun hale getirilmesi amacıyla istenilmez ve yapılmaz.  \n(Değişik ikinci fıkra: 20/11/2008-5812/11 md.) Tekliflerin değerlendirilmesinde, \nöncelikle belgeleri eksik olduğu veya teklif mektubu ile geçici teminatı usulüne uygun olmadığı \n36 ncı maddeye göre ilk oturumda tespit edilen isteklilerin tekliflerinin değerlendirme dışı \nbırakılmasına karar verilir. Ancak, teklifin esasını değiştirecek nitelikte olmaması kaydıyla, \nbelgelerde bilgi eksikliği bulunması halinde idarece belirlenen sürede isteklilerden bu eksik \nbilgilerin tamamlanması yazılı olarak istenir. Belirlenen sürede bilgileri tamamlamayan istekliler \ndeğerlendirme dışı bırakılır ve geçici teminatları gelir kaydedilir. Bu ilk değerlendirme ve \nişlemler sonucunda belgeleri eksiksiz ve teklif mektubu ile geçici teminatı usulüne uygun olan \nisteklilerin tekliflerinin ayrıntılı değerlendirilmesine geçilir. Bu aşamada, isteklilerin ihale konusu \nişi yapabilme kapasitelerini belirleyen yeterlik kriterlerine ve tekliflerin ihale dokümanında \nbelirtilen şartlara uygun olup olmadığı ile birim fiyat teklif cetvellerinde aritmetik hata bulunup \nbulunmadığı incelenir. Uygun olmadığı belirlenen isteklilerin teklifleri ile birim fiyat teklif \ncetvellerinde aritmetik hata bulunan teklifler değerlendirme dışı bırakılır. \n(Mülga son fıkra: 20/11/2008-5812/11 md.) \n \n36 20/11/2008 tarihli ve 5812 sayılı Kanunun 10 uncu maddesiyle; bu fıkrada yer alan “teklif fiyatları \naçıklanır” ibaresi “teklif fiyatları ve yaklaşık maliyet tutarı açıklanır” şeklinde değiştirilmiştir. \n\n \nAşırı düşük teklifler",
      "source": "4734",
      "rag_domain": "legal",
      "law_number": "4734",
      "document_id": null,
      "madde_no": "37",
      "article": "37",
      "trusted_source": true,
      "metadata": {
        "rag_eligible": true,
        "law_number": "4734",
        "rag_domain": "legal",
        "madde_no": "37",
        "source": "4734",
        "title": "Kamu İhale Kanunu (4734)",
        "trusted_source": true
      }
    }
  ],
  "retrieved_sources": [
    {
      "score": 0.56865597,
      "chunk_id": "0c698c92-161c-500d-9a33-d275292f7c8a",
      "title": "Kamu İhale Kanunu (4734)",
      "text": "Madde 56- (Değişik: 22/11/2008-5812/23 md.) \nİdareye şikayet başvurusunda bulunan veya idarece alınan kararı uygun bulmayan aday, \nistekli veya istekli olabilecekler tarafından 55 inci maddenin dördüncü fıkrasında belirtilen \nhallerde ve sürede, sözleşme imzalanmadan önce itirazen şikayet başvurusunda bulunulabilir. \nİhalenin iptaline ilişkin işlem ve kararlardan, sadece şikayet ve itirazen şikayet üzerine alınanlar \nitirazen şikayete konu edilebilir ve bu kararlara karşı beş gün içinde doğrudan Kuruma başvuruda \nbulunulabilir. \nKurum itirazen şikayet başvurularını başvuru sahibinin iddiaları ile idarenin şikayet \nüzerine aldığı kararda belirlenen hususlar ve itiraz edilen işlemler bakımından eşit muamele \nilkesinin ihlal edilip edilmediği açılarından inceler. İdare tarafından şikayet veya itirazen şikayet \nüzerine alınan ihalenin iptal edilmesi işlemine karşı yapılacak itirazen şikayet başvuruları ise \nidarenin iptal gerekçeleriyle sınırlı incelenir. \nKanunda belirtilen sürelere ve usule uyulmadan sözleşme imzalanmış olması veya itirazen \nşikayet başvurusundan feragat edilmesi itirazen şikayet başvurusunun incelenmesine ve 54 üncü \nmaddede sayılan kararlardan birinin alınmasına engel teşkil etmez. \n \n60 20/11/2008 tarihli ve 5812 sayılı Kanunun 23 üncü maddesiyle bu madde başlığı “Kamu İhale Kurulu \ntarafından inceleme” iken, 5/1/2009 tarihinden geçerli olmak üzere metne işlendiği şekilde \ndeğiştirilmiştir. \n\nKurul tarafından gerekli görülen hallerde tarafların ve ilgililerin dinlenmesine karar \nverilir. Bu durumda, Kurul tarafından tespit edilen tarihte taraflar ve ilgililer dinlenir. \nKurum, itirazen şikayete ilişkin nihai kararını, incelenen ihaleye ilişkin gerekli bilgi ve \nbelgeler ile ihale işlem dosyasının kayıtlara alındığı tarihi izleyen yirmi gün içinde vermek \nzorundadır. Bu süre 21 inci maddenin (b) ve (c) bentlerine göre yapılan ihaleler ile şikayet ve \nitirazen şikayet üzerine alınan ihalenin iptal edilmesi işlemine karşı yapılacak itirazen şikayet \nb",
      "source": "4734",
      "rag_domain": "legal",
      "law_number": "4734",
      "document_id": null,
      "madde_no": "56",
      "article": "56",
      "trusted_source": true,
      "metadata": {
        "rag_eligible": true,
        "law_number": "4734",
        "rag_domain": "legal",
        "madde_no": "56",
        "source": "4734",
        "title": "Kamu İhale Kanunu (4734)",
        "trusted_source": true
      }
    },
    {
      "score": 0.5609256,
      "chunk_id": "1fffd493-df26-5842-910e-81bad6d09500",
      "title": "Kamu İhale Kanunu (4734)",
      "text": "Madde 54- (Değişik: 20/11/2008-5812/21 md.)  \nİhale sürecindeki hukuka aykırı işlem veya eylemler nedeniyle bir hak kaybına veya \nzarara uğradığını veya zarara uğramasının muhtemel olduğunu iddia eden aday veya istekli ile \nistekli olabilecekler, bu Kanunda belirtilen şekil ve usul kurallarına uygun olmak şartıyla şikayet \nve itirazen şikayet başvurusunda bulunabilirler. \nŞikayet ve itirazen şikayet başvuruları, dava açılmadan önce tüketilmesi zorunlu idari \nbaşvuru yollarıdır. \nŞikayet başvuruları idareye, itirazen şikayet başvuruları Kuruma hitaben yazılmış imzalı \ndilekçelerle yapılır.  \nDilekçelerde aşağıdaki hususlara yer verilir: \na) Başvuru sahibinin, varsa vekil ya da temsilcisinin adı, soyadı veya unvanı ve adresi. \nb) İhaleyi yapan idarenin ve ihalenin adı veya ihale kayıt numarası. \nc) Başvuruya konu olan durumun farkına varıldığı veya bildirildiği tarih. \nd) Başvurunun konusu, sebepleri ve dayandığı deliller. \ne) İtirazen şikayet başvurularında idareye yapılan şikayetin ve varsa şikayete ilişkin idare \nkararının bildirim tarihi. \n(Değişik beşinci fıkra:28/1/2021-7263/10 md.) Şikâyet ve itirazen şikâyet başvuru \ndilekçelerinde yer alması gereken diğer bilgiler ile bu dilekçelere eklenmesi gereken belgelere, \nbunların sunuluş şekli ile bu başvuruların elektronik ortamda yapılmasına ilişkin usul ve esasları \nbelirlemeye Kurum yetkilidir.  \nİtirazen şikayette bulunanlardan 53 üncü maddenin (j) bendinin (2) nolu alt bendinde \nbelirtilen bedelin dört katı tutarına kadar başvuru teminatı alınmasına Cumhurbaşkanınca karar \nverilebilir. Başvuru teminatları Kurum hesaplarına yatırılır. Bu teminatlar Kurum gelirleri ile \nilişkilendirilmeksizin ayrı hesaplarda tutulur.58 \n(Mülga yedinci fıkra:28/1/2021-7263/10 md.)  \nAynı kişi tarafından birden fazla ihaleye, birden fazla kişi tarafından ise aynı ihaleye tek \ndilekçe ile başvuruda bulunulamaz. \n(Ek: 6/2/2014-6518/50 md.) Başvuruların ihaleyi yapan idare veya Kurum dışındaki idari \n \n56 20/11/2008 tarihli ve 5812 say",
      "source": "4734",
      "rag_domain": "legal",
      "law_number": "4734",
      "document_id": null,
      "madde_no": "54",
      "article": "54",
      "trusted_source": true,
      "metadata": {
        "rag_eligible": true,
        "law_number": "4734",
        "rag_domain": "legal",
        "madde_no": "54",
        "source": "4734",
        "title": "Kamu İhale Kanunu (4734)",
        "trusted_source": true
      }
    },
    {
      "score": 0.5538851,
      "chunk_id": "213251bd-4eeb-512f-af39-42ed2e69083f",
      "title": "Kamu İhale Kanunu (4734)",
      "text": "Madde 37- İhale komisyonunun talebi üzerine idare tekliflerin incelenmesi, \nkarşılaştırılması ve değerlendirilmesinde yararlanmak üzere net olmayan hususlarla ilgili \nisteklilerden yazılı olarak tekliflerini açıklamalarını isteyebilir. Ancak bu açıklama, hiçbir şekilde \nteklif fiyatında değişiklik yapılması veya ihale dokümanında yer alan şartlara uygun olmayan \ntekliflerin uygun hale getirilmesi amacıyla istenilmez ve yapılmaz.  \n(Değişik ikinci fıkra: 20/11/2008-5812/11 md.) Tekliflerin değerlendirilmesinde, \nöncelikle belgeleri eksik olduğu veya teklif mektubu ile geçici teminatı usulüne uygun olmadığı \n36 ncı maddeye göre ilk oturumda tespit edilen isteklilerin tekliflerinin değerlendirme dışı \nbırakılmasına karar verilir. Ancak, teklifin esasını değiştirecek nitelikte olmaması kaydıyla, \nbelgelerde bilgi eksikliği bulunması halinde idarece belirlenen sürede isteklilerden bu eksik \nbilgilerin tamamlanması yazılı olarak istenir. Belirlenen sürede bilgileri tamamlamayan istekliler \ndeğerlendirme dışı bırakılır ve geçici teminatları gelir kaydedilir. Bu ilk değerlendirme ve \nişlemler sonucunda belgeleri eksiksiz ve teklif mektubu ile geçici teminatı usulüne uygun olan \nisteklilerin tekliflerinin ayrıntılı değerlendirilmesine geçilir. Bu aşamada, isteklilerin ihale konusu \nişi yapabilme kapasitelerini belirleyen yeterlik kriterlerine ve tekliflerin ihale dokümanında \nbelirtilen şartlara uygun olup olmadığı ile birim fiyat teklif cetvellerinde aritmetik hata bulunup \nbulunmadığı incelenir. Uygun olmadığı belirlenen isteklilerin teklifleri ile birim fiyat teklif \ncetvellerinde aritmetik hata bulunan teklifler değerlendirme dışı bırakılır. \n(Mülga son fıkra: 20/11/2008-5812/11 md.) \n \n36 20/11/2008 tarihli ve 5812 sayılı Kanunun 10 uncu maddesiyle; bu fıkrada yer alan “teklif fiyatları \naçıklanır” ibaresi “teklif fiyatları ve yaklaşık maliyet tutarı açıklanır” şeklinde değiştirilmiştir. \n\n \nAşırı düşük teklifler",
      "source": "4734",
      "rag_domain": "legal",
      "law_number": "4734",
      "document_id": null,
      "madde_no": "37",
      "article": "37",
      "trusted_source": true,
      "metadata": {
        "rag_eligible": true,
        "law_number": "4734",
        "rag_domain": "legal",
        "madde_no": "37",
        "source": "4734",
        "title": "Kamu İhale Kanunu (4734)",
        "trusted_source": true
      }
    },
    {
      "score": 0.5187256,
      "chunk_id": "a9dd4747-35f6-5168-a61b-174631ac25ef",
      "title": "Kamu İhale Kanunu (4734)",
      "text": "Madde 55- (Değişik: 20/11/2008-5812/22 md.) \nŞikayet başvurusu, ihale sürecindeki işlem veya eylemlerin hukuka aykırılığı iddiasıyla bu \nişlem veya eylemlerin farkına varıldığı veya farkına varılmış olması gereken tarihi izleyen \ngünden itibaren 21 inci maddenin (b) ve (c) bentlerine göre yapılan ihalelerde beş gün, diğer \nhallerde ise on gün içinde ve sözleşmenin imzalanmasından önce, ihaleyi yapan idareye yapılır. \nİlanda yer alan hususlara yönelik başvuruların süresi ilk ilan tarihinden, ön yeterlik veya ihale \ndokümanının ilana yansımayan diğer hükümlerine yönelik başvuruların süresi ise dokümanın \nsatın alındığı tarihte başlar. \nİlan, ön yeterlik veya ihale dokümanına ilişkin şikayetler birinci fıkradaki süreleri aşmamak \nüzere en geç ihale veya son başvuru tarihinden üç iş günü öncesine kadar yapılabilir. Bu yöndeki \nbaşvuruların idarelerce ihale veya son başvuru tarihinden önce sonuçlandırılması esastır. Şikayet \nüzerine yapılan incelemede tekliflerin hazırlanmasını veya işin gerçekleştirilmesini etkileyebilecek \nmaddi veya teknik hataların veya eksikliklerin bulunması ve idarece ihale dokümanında düzeltme \nyapılmasına karar verilmesi halinde, gerekli düzeltme yapılarak 29 uncu maddede belirtilen usule \n \n59 20/11/2008 tarihli ve 5812 sayılı Kanunun 21 inci maddesiyle bu madde başlığı “İdare tarafından \ninceleme” iken, metne işlendiği şekilde değiştirilmiştir. \n\ngöre son başvuru veya ihale tarihi bir defaya mahsus olmak üzere ertelenir. Ancak belirlenen maddi \nveya teknik hataların veya eksikliklerin ilanda da bulunması halinde 26 ncı maddeye göre işlem \ntesis edilir. \nİdare, şikayet başvurusu üzerine gerekli incelemeyi yaparak on gün içinde gerekçeli bir \nkarar alır. Alınan karar, şikayetçi ile diğer aday veya istekliler ile istekli olabileceklere karar \ntarihini izleyen üç gün içinde bildirilir. İlan ile ihale veya ön yeterlik dokümanına yönelik \nbaşvurular dışında istekli olabileceklere bildirim yapılmaz. \nBelirtilen süre içinde bir karar alınmaması durumu",
      "source": "4734",
      "rag_domain": "legal",
      "law_number": "4734",
      "document_id": null,
      "madde_no": "55",
      "article": "55",
      "trusted_source": true,
      "metadata": {
        "rag_eligible": true,
        "law_number": "4734",
        "rag_domain": "legal",
        "madde_no": "55",
        "source": "4734",
        "title": "Kamu İhale Kanunu (4734)",
        "trusted_source": true
      }
    },
    {
      "score": 0.51385796,
      "chunk_id": "77df74b5-a77d-5701-bbc2-c3d0c54961b5",
      "title": "Tüketicinin Korunması Hakkında Kanun (6502)",
      "text": "MADDE 69- (1) Tüketici hakem heyetleri uyuşmazlık konusuna ilişkin her türlü bilgi \nve belgeyi taraflardan, ilgili kurum veya kuruluşlardan isteyebilir.  \n \nKarar ve karara itiraz",
      "source": "6502",
      "rag_domain": "legal",
      "law_number": "6502",
      "document_id": null,
      "madde_no": "69",
      "article": "69",
      "trusted_source": true,
      "metadata": {
        "rag_eligible": true,
        "law_number": "6502",
        "rag_domain": "legal",
        "madde_no": "69",
        "source": "6502",
        "title": "Tüketicinin Korunması Hakkında Kanun (6502)",
        "trusted_source": true
      }
    }
  ],
  "retrieval_score": 0.5687,
  "confidence_type": "retrieval_score",
  "llm": {
    "provider": "evren",
    "model": "llm-large"
  }
}
```
### missing_field_agent

**Tam tüketilen giriş:**

```json
{
  "document.document_type": "dilekce",
  "document.process_intent": "basvuru",
  "extraction.fields": {
    "signature_present": {
      "value": null,
      "status": "unknown",
      "evidence": null,
      "source": "document",
      "method": "deterministic",
      "validated": true
    },
    "authority_document_present": {
      "value": null,
      "status": "unknown",
      "evidence": null,
      "source": "document",
      "method": "deterministic",
      "validated": true
    },
    "subject": {
      "value": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
      "evidence": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
      "source": "document",
      "method": "document_agent",
      "validated": true
    },
    "request": {
      "value": "idari inceleme talep ediyoruz",
      "evidence": "idari inceleme talep ediyoruz",
      "source": "document",
      "method": "document_agent",
      "validated": true
    },
    "person_name": {
      "value": "Polat Madencilik adına Pelin Sönmez",
      "evidence": "BAŞVURAN: Polat Madencilik adına Pelin Sönmez",
      "source": "document",
      "method": "deterministic",
      "validated": true
    },
    "address": {
      "value": "Örenli İlçe Kaymakamlığı",
      "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA",
      "source": "document",
      "method": "llm",
      "validated": true
    },
    "institution": {
      "value": "Örenli İlçe Kaymakamlığı",
      "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA",
      "source": "document",
      "method": "llm",
      "validated": true
    },
    "sender_unit": {
      "value": "Polat Madencilik",
      "evidence": "Polat Madencilik",
      "source": "document",
      "method": "llm",
      "validated": true
    },
    "recipient": {
      "value": "Örenli İlçe Kaymakamlığı",
      "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA",
      "source": "document",
      "method": "llm",
      "validated": true
    },
    "other_entities": {
      "value": [
        {
          "type": "organization",
          "value": "Polat Madencilik",
          "evidence": "Polat Madencilik"
        },
        {
          "type": "organization",
          "value": "Polat Madencilik",
          "evidence": "Polat Madencilik"
        }
      ],
      "evidence": [
        "Polat Madencilik",
        "Polat Madencilik"
      ],
      "source": "document",
      "method": "llm",
      "validated": true
    }
  },
  "legal_analysis": {
    "answer": "Sağlanan kaynaklarda soruya ilişkin doğrulanabilir bir bilgi çıkarılamadı.",
    "evidence": [],
    "sources": [
      {
        "score": 0.56865597,
        "chunk_id": "0c698c92-161c-500d-9a33-d275292f7c8a",
        "title": "Kamu İhale Kanunu (4734)",
        "text": "Madde 56- (Değişik: 22/11/2008-5812/23 md.) \nİdareye şikayet başvurusunda bulunan veya idarece alınan kararı uygun bulmayan aday, \nistekli veya istekli olabilecekler tarafından 55 inci maddenin dördüncü fıkrasında belirtilen \nhallerde ve sürede, sözleşme imzalanmadan önce itirazen şikayet başvurusunda bulunulabilir. \nİhalenin iptaline ilişkin işlem ve kararlardan, sadece şikayet ve itirazen şikayet üzerine alınanlar \nitirazen şikayete konu edilebilir ve bu kararlara karşı beş gün içinde doğrudan Kuruma başvuruda \nbulunulabilir. \nKurum itirazen şikayet başvurularını başvuru sahibinin iddiaları ile idarenin şikayet \nüzerine aldığı kararda belirlenen hususlar ve itiraz edilen işlemler bakımından eşit muamele \nilkesinin ihlal edilip edilmediği açılarından inceler. İdare tarafından şikayet veya itirazen şikayet \nüzerine alınan ihalenin iptal edilmesi işlemine karşı yapılacak itirazen şikayet başvuruları ise \nidarenin iptal gerekçeleriyle sınırlı incelenir. \nKanunda belirtilen sürelere ve usule uyulmadan sözleşme imzalanmış olması veya itirazen \nşikayet başvurusundan feragat edilmesi itirazen şikayet başvurusunun incelenmesine ve 54 üncü \nmaddede sayılan kararlardan birinin alınmasına engel teşkil etmez. \n \n60 20/11/2008 tarihli ve 5812 sayılı Kanunun 23 üncü maddesiyle bu madde başlığı “Kamu İhale Kurulu \ntarafından inceleme” iken, 5/1/2009 tarihinden geçerli olmak üzere metne işlendiği şekilde \ndeğiştirilmiştir. \n\nKurul tarafından gerekli görülen hallerde tarafların ve ilgililerin dinlenmesine karar \nverilir. Bu durumda, Kurul tarafından tespit edilen tarihte taraflar ve ilgililer dinlenir. \nKurum, itirazen şikayete ilişkin nihai kararını, incelenen ihaleye ilişkin gerekli bilgi ve \nbelgeler ile ihale işlem dosyasının kayıtlara alındığı tarihi izleyen yirmi gün içinde vermek \nzorundadır. Bu süre 21 inci maddenin (b) ve (c) bentlerine göre yapılan ihaleler ile şikayet ve \nitirazen şikayet üzerine alınan ihalenin iptal edilmesi işlemine karşı yapılacak itirazen şikayet \nb",
        "source": "4734",
        "rag_domain": "legal",
        "law_number": "4734",
        "document_id": null,
        "madde_no": "56",
        "article": "56",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "4734",
          "rag_domain": "legal",
          "madde_no": "56",
          "source": "4734",
          "title": "Kamu İhale Kanunu (4734)",
          "trusted_source": true
        }
      },
      {
        "score": 0.5609256,
        "chunk_id": "1fffd493-df26-5842-910e-81bad6d09500",
        "title": "Kamu İhale Kanunu (4734)",
        "text": "Madde 54- (Değişik: 20/11/2008-5812/21 md.)  \nİhale sürecindeki hukuka aykırı işlem veya eylemler nedeniyle bir hak kaybına veya \nzarara uğradığını veya zarara uğramasının muhtemel olduğunu iddia eden aday veya istekli ile \nistekli olabilecekler, bu Kanunda belirtilen şekil ve usul kurallarına uygun olmak şartıyla şikayet \nve itirazen şikayet başvurusunda bulunabilirler. \nŞikayet ve itirazen şikayet başvuruları, dava açılmadan önce tüketilmesi zorunlu idari \nbaşvuru yollarıdır. \nŞikayet başvuruları idareye, itirazen şikayet başvuruları Kuruma hitaben yazılmış imzalı \ndilekçelerle yapılır.  \nDilekçelerde aşağıdaki hususlara yer verilir: \na) Başvuru sahibinin, varsa vekil ya da temsilcisinin adı, soyadı veya unvanı ve adresi. \nb) İhaleyi yapan idarenin ve ihalenin adı veya ihale kayıt numarası. \nc) Başvuruya konu olan durumun farkına varıldığı veya bildirildiği tarih. \nd) Başvurunun konusu, sebepleri ve dayandığı deliller. \ne) İtirazen şikayet başvurularında idareye yapılan şikayetin ve varsa şikayete ilişkin idare \nkararının bildirim tarihi. \n(Değişik beşinci fıkra:28/1/2021-7263/10 md.) Şikâyet ve itirazen şikâyet başvuru \ndilekçelerinde yer alması gereken diğer bilgiler ile bu dilekçelere eklenmesi gereken belgelere, \nbunların sunuluş şekli ile bu başvuruların elektronik ortamda yapılmasına ilişkin usul ve esasları \nbelirlemeye Kurum yetkilidir.  \nİtirazen şikayette bulunanlardan 53 üncü maddenin (j) bendinin (2) nolu alt bendinde \nbelirtilen bedelin dört katı tutarına kadar başvuru teminatı alınmasına Cumhurbaşkanınca karar \nverilebilir. Başvuru teminatları Kurum hesaplarına yatırılır. Bu teminatlar Kurum gelirleri ile \nilişkilendirilmeksizin ayrı hesaplarda tutulur.58 \n(Mülga yedinci fıkra:28/1/2021-7263/10 md.)  \nAynı kişi tarafından birden fazla ihaleye, birden fazla kişi tarafından ise aynı ihaleye tek \ndilekçe ile başvuruda bulunulamaz. \n(Ek: 6/2/2014-6518/50 md.) Başvuruların ihaleyi yapan idare veya Kurum dışındaki idari \n \n56 20/11/2008 tarihli ve 5812 say",
        "source": "4734",
        "rag_domain": "legal",
        "law_number": "4734",
        "document_id": null,
        "madde_no": "54",
        "article": "54",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "4734",
          "rag_domain": "legal",
          "madde_no": "54",
          "source": "4734",
          "title": "Kamu İhale Kanunu (4734)",
          "trusted_source": true
        }
      },
      {
        "score": 0.5538851,
        "chunk_id": "213251bd-4eeb-512f-af39-42ed2e69083f",
        "title": "Kamu İhale Kanunu (4734)",
        "text": "Madde 37- İhale komisyonunun talebi üzerine idare tekliflerin incelenmesi, \nkarşılaştırılması ve değerlendirilmesinde yararlanmak üzere net olmayan hususlarla ilgili \nisteklilerden yazılı olarak tekliflerini açıklamalarını isteyebilir. Ancak bu açıklama, hiçbir şekilde \nteklif fiyatında değişiklik yapılması veya ihale dokümanında yer alan şartlara uygun olmayan \ntekliflerin uygun hale getirilmesi amacıyla istenilmez ve yapılmaz.  \n(Değişik ikinci fıkra: 20/11/2008-5812/11 md.) Tekliflerin değerlendirilmesinde, \nöncelikle belgeleri eksik olduğu veya teklif mektubu ile geçici teminatı usulüne uygun olmadığı \n36 ncı maddeye göre ilk oturumda tespit edilen isteklilerin tekliflerinin değerlendirme dışı \nbırakılmasına karar verilir. Ancak, teklifin esasını değiştirecek nitelikte olmaması kaydıyla, \nbelgelerde bilgi eksikliği bulunması halinde idarece belirlenen sürede isteklilerden bu eksik \nbilgilerin tamamlanması yazılı olarak istenir. Belirlenen sürede bilgileri tamamlamayan istekliler \ndeğerlendirme dışı bırakılır ve geçici teminatları gelir kaydedilir. Bu ilk değerlendirme ve \nişlemler sonucunda belgeleri eksiksiz ve teklif mektubu ile geçici teminatı usulüne uygun olan \nisteklilerin tekliflerinin ayrıntılı değerlendirilmesine geçilir. Bu aşamada, isteklilerin ihale konusu \nişi yapabilme kapasitelerini belirleyen yeterlik kriterlerine ve tekliflerin ihale dokümanında \nbelirtilen şartlara uygun olup olmadığı ile birim fiyat teklif cetvellerinde aritmetik hata bulunup \nbulunmadığı incelenir. Uygun olmadığı belirlenen isteklilerin teklifleri ile birim fiyat teklif \ncetvellerinde aritmetik hata bulunan teklifler değerlendirme dışı bırakılır. \n(Mülga son fıkra: 20/11/2008-5812/11 md.) \n \n36 20/11/2008 tarihli ve 5812 sayılı Kanunun 10 uncu maddesiyle; bu fıkrada yer alan “teklif fiyatları \naçıklanır” ibaresi “teklif fiyatları ve yaklaşık maliyet tutarı açıklanır” şeklinde değiştirilmiştir. \n\n \nAşırı düşük teklifler",
        "source": "4734",
        "rag_domain": "legal",
        "law_number": "4734",
        "document_id": null,
        "madde_no": "37",
        "article": "37",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "4734",
          "rag_domain": "legal",
          "madde_no": "37",
          "source": "4734",
          "title": "Kamu İhale Kanunu (4734)",
          "trusted_source": true
        }
      }
    ],
    "retrieved_sources": [
      {
        "score": 0.56865597,
        "chunk_id": "0c698c92-161c-500d-9a33-d275292f7c8a",
        "title": "Kamu İhale Kanunu (4734)",
        "text": "Madde 56- (Değişik: 22/11/2008-5812/23 md.) \nİdareye şikayet başvurusunda bulunan veya idarece alınan kararı uygun bulmayan aday, \nistekli veya istekli olabilecekler tarafından 55 inci maddenin dördüncü fıkrasında belirtilen \nhallerde ve sürede, sözleşme imzalanmadan önce itirazen şikayet başvurusunda bulunulabilir. \nİhalenin iptaline ilişkin işlem ve kararlardan, sadece şikayet ve itirazen şikayet üzerine alınanlar \nitirazen şikayete konu edilebilir ve bu kararlara karşı beş gün içinde doğrudan Kuruma başvuruda \nbulunulabilir. \nKurum itirazen şikayet başvurularını başvuru sahibinin iddiaları ile idarenin şikayet \nüzerine aldığı kararda belirlenen hususlar ve itiraz edilen işlemler bakımından eşit muamele \nilkesinin ihlal edilip edilmediği açılarından inceler. İdare tarafından şikayet veya itirazen şikayet \nüzerine alınan ihalenin iptal edilmesi işlemine karşı yapılacak itirazen şikayet başvuruları ise \nidarenin iptal gerekçeleriyle sınırlı incelenir. \nKanunda belirtilen sürelere ve usule uyulmadan sözleşme imzalanmış olması veya itirazen \nşikayet başvurusundan feragat edilmesi itirazen şikayet başvurusunun incelenmesine ve 54 üncü \nmaddede sayılan kararlardan birinin alınmasına engel teşkil etmez. \n \n60 20/11/2008 tarihli ve 5812 sayılı Kanunun 23 üncü maddesiyle bu madde başlığı “Kamu İhale Kurulu \ntarafından inceleme” iken, 5/1/2009 tarihinden geçerli olmak üzere metne işlendiği şekilde \ndeğiştirilmiştir. \n\nKurul tarafından gerekli görülen hallerde tarafların ve ilgililerin dinlenmesine karar \nverilir. Bu durumda, Kurul tarafından tespit edilen tarihte taraflar ve ilgililer dinlenir. \nKurum, itirazen şikayete ilişkin nihai kararını, incelenen ihaleye ilişkin gerekli bilgi ve \nbelgeler ile ihale işlem dosyasının kayıtlara alındığı tarihi izleyen yirmi gün içinde vermek \nzorundadır. Bu süre 21 inci maddenin (b) ve (c) bentlerine göre yapılan ihaleler ile şikayet ve \nitirazen şikayet üzerine alınan ihalenin iptal edilmesi işlemine karşı yapılacak itirazen şikayet \nb",
        "source": "4734",
        "rag_domain": "legal",
        "law_number": "4734",
        "document_id": null,
        "madde_no": "56",
        "article": "56",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "4734",
          "rag_domain": "legal",
          "madde_no": "56",
          "source": "4734",
          "title": "Kamu İhale Kanunu (4734)",
          "trusted_source": true
        }
      },
      {
        "score": 0.5609256,
        "chunk_id": "1fffd493-df26-5842-910e-81bad6d09500",
        "title": "Kamu İhale Kanunu (4734)",
        "text": "Madde 54- (Değişik: 20/11/2008-5812/21 md.)  \nİhale sürecindeki hukuka aykırı işlem veya eylemler nedeniyle bir hak kaybına veya \nzarara uğradığını veya zarara uğramasının muhtemel olduğunu iddia eden aday veya istekli ile \nistekli olabilecekler, bu Kanunda belirtilen şekil ve usul kurallarına uygun olmak şartıyla şikayet \nve itirazen şikayet başvurusunda bulunabilirler. \nŞikayet ve itirazen şikayet başvuruları, dava açılmadan önce tüketilmesi zorunlu idari \nbaşvuru yollarıdır. \nŞikayet başvuruları idareye, itirazen şikayet başvuruları Kuruma hitaben yazılmış imzalı \ndilekçelerle yapılır.  \nDilekçelerde aşağıdaki hususlara yer verilir: \na) Başvuru sahibinin, varsa vekil ya da temsilcisinin adı, soyadı veya unvanı ve adresi. \nb) İhaleyi yapan idarenin ve ihalenin adı veya ihale kayıt numarası. \nc) Başvuruya konu olan durumun farkına varıldığı veya bildirildiği tarih. \nd) Başvurunun konusu, sebepleri ve dayandığı deliller. \ne) İtirazen şikayet başvurularında idareye yapılan şikayetin ve varsa şikayete ilişkin idare \nkararının bildirim tarihi. \n(Değişik beşinci fıkra:28/1/2021-7263/10 md.) Şikâyet ve itirazen şikâyet başvuru \ndilekçelerinde yer alması gereken diğer bilgiler ile bu dilekçelere eklenmesi gereken belgelere, \nbunların sunuluş şekli ile bu başvuruların elektronik ortamda yapılmasına ilişkin usul ve esasları \nbelirlemeye Kurum yetkilidir.  \nİtirazen şikayette bulunanlardan 53 üncü maddenin (j) bendinin (2) nolu alt bendinde \nbelirtilen bedelin dört katı tutarına kadar başvuru teminatı alınmasına Cumhurbaşkanınca karar \nverilebilir. Başvuru teminatları Kurum hesaplarına yatırılır. Bu teminatlar Kurum gelirleri ile \nilişkilendirilmeksizin ayrı hesaplarda tutulur.58 \n(Mülga yedinci fıkra:28/1/2021-7263/10 md.)  \nAynı kişi tarafından birden fazla ihaleye, birden fazla kişi tarafından ise aynı ihaleye tek \ndilekçe ile başvuruda bulunulamaz. \n(Ek: 6/2/2014-6518/50 md.) Başvuruların ihaleyi yapan idare veya Kurum dışındaki idari \n \n56 20/11/2008 tarihli ve 5812 say",
        "source": "4734",
        "rag_domain": "legal",
        "law_number": "4734",
        "document_id": null,
        "madde_no": "54",
        "article": "54",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "4734",
          "rag_domain": "legal",
          "madde_no": "54",
          "source": "4734",
          "title": "Kamu İhale Kanunu (4734)",
          "trusted_source": true
        }
      },
      {
        "score": 0.5538851,
        "chunk_id": "213251bd-4eeb-512f-af39-42ed2e69083f",
        "title": "Kamu İhale Kanunu (4734)",
        "text": "Madde 37- İhale komisyonunun talebi üzerine idare tekliflerin incelenmesi, \nkarşılaştırılması ve değerlendirilmesinde yararlanmak üzere net olmayan hususlarla ilgili \nisteklilerden yazılı olarak tekliflerini açıklamalarını isteyebilir. Ancak bu açıklama, hiçbir şekilde \nteklif fiyatında değişiklik yapılması veya ihale dokümanında yer alan şartlara uygun olmayan \ntekliflerin uygun hale getirilmesi amacıyla istenilmez ve yapılmaz.  \n(Değişik ikinci fıkra: 20/11/2008-5812/11 md.) Tekliflerin değerlendirilmesinde, \nöncelikle belgeleri eksik olduğu veya teklif mektubu ile geçici teminatı usulüne uygun olmadığı \n36 ncı maddeye göre ilk oturumda tespit edilen isteklilerin tekliflerinin değerlendirme dışı \nbırakılmasına karar verilir. Ancak, teklifin esasını değiştirecek nitelikte olmaması kaydıyla, \nbelgelerde bilgi eksikliği bulunması halinde idarece belirlenen sürede isteklilerden bu eksik \nbilgilerin tamamlanması yazılı olarak istenir. Belirlenen sürede bilgileri tamamlamayan istekliler \ndeğerlendirme dışı bırakılır ve geçici teminatları gelir kaydedilir. Bu ilk değerlendirme ve \nişlemler sonucunda belgeleri eksiksiz ve teklif mektubu ile geçici teminatı usulüne uygun olan \nisteklilerin tekliflerinin ayrıntılı değerlendirilmesine geçilir. Bu aşamada, isteklilerin ihale konusu \nişi yapabilme kapasitelerini belirleyen yeterlik kriterlerine ve tekliflerin ihale dokümanında \nbelirtilen şartlara uygun olup olmadığı ile birim fiyat teklif cetvellerinde aritmetik hata bulunup \nbulunmadığı incelenir. Uygun olmadığı belirlenen isteklilerin teklifleri ile birim fiyat teklif \ncetvellerinde aritmetik hata bulunan teklifler değerlendirme dışı bırakılır. \n(Mülga son fıkra: 20/11/2008-5812/11 md.) \n \n36 20/11/2008 tarihli ve 5812 sayılı Kanunun 10 uncu maddesiyle; bu fıkrada yer alan “teklif fiyatları \naçıklanır” ibaresi “teklif fiyatları ve yaklaşık maliyet tutarı açıklanır” şeklinde değiştirilmiştir. \n\n \nAşırı düşük teklifler",
        "source": "4734",
        "rag_domain": "legal",
        "law_number": "4734",
        "document_id": null,
        "madde_no": "37",
        "article": "37",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "4734",
          "rag_domain": "legal",
          "madde_no": "37",
          "source": "4734",
          "title": "Kamu İhale Kanunu (4734)",
          "trusted_source": true
        }
      },
      {
        "score": 0.5187256,
        "chunk_id": "a9dd4747-35f6-5168-a61b-174631ac25ef",
        "title": "Kamu İhale Kanunu (4734)",
        "text": "Madde 55- (Değişik: 20/11/2008-5812/22 md.) \nŞikayet başvurusu, ihale sürecindeki işlem veya eylemlerin hukuka aykırılığı iddiasıyla bu \nişlem veya eylemlerin farkına varıldığı veya farkına varılmış olması gereken tarihi izleyen \ngünden itibaren 21 inci maddenin (b) ve (c) bentlerine göre yapılan ihalelerde beş gün, diğer \nhallerde ise on gün içinde ve sözleşmenin imzalanmasından önce, ihaleyi yapan idareye yapılır. \nİlanda yer alan hususlara yönelik başvuruların süresi ilk ilan tarihinden, ön yeterlik veya ihale \ndokümanının ilana yansımayan diğer hükümlerine yönelik başvuruların süresi ise dokümanın \nsatın alındığı tarihte başlar. \nİlan, ön yeterlik veya ihale dokümanına ilişkin şikayetler birinci fıkradaki süreleri aşmamak \nüzere en geç ihale veya son başvuru tarihinden üç iş günü öncesine kadar yapılabilir. Bu yöndeki \nbaşvuruların idarelerce ihale veya son başvuru tarihinden önce sonuçlandırılması esastır. Şikayet \nüzerine yapılan incelemede tekliflerin hazırlanmasını veya işin gerçekleştirilmesini etkileyebilecek \nmaddi veya teknik hataların veya eksikliklerin bulunması ve idarece ihale dokümanında düzeltme \nyapılmasına karar verilmesi halinde, gerekli düzeltme yapılarak 29 uncu maddede belirtilen usule \n \n59 20/11/2008 tarihli ve 5812 sayılı Kanunun 21 inci maddesiyle bu madde başlığı “İdare tarafından \ninceleme” iken, metne işlendiği şekilde değiştirilmiştir. \n\ngöre son başvuru veya ihale tarihi bir defaya mahsus olmak üzere ertelenir. Ancak belirlenen maddi \nveya teknik hataların veya eksikliklerin ilanda da bulunması halinde 26 ncı maddeye göre işlem \ntesis edilir. \nİdare, şikayet başvurusu üzerine gerekli incelemeyi yaparak on gün içinde gerekçeli bir \nkarar alır. Alınan karar, şikayetçi ile diğer aday veya istekliler ile istekli olabileceklere karar \ntarihini izleyen üç gün içinde bildirilir. İlan ile ihale veya ön yeterlik dokümanına yönelik \nbaşvurular dışında istekli olabileceklere bildirim yapılmaz. \nBelirtilen süre içinde bir karar alınmaması durumu",
        "source": "4734",
        "rag_domain": "legal",
        "law_number": "4734",
        "document_id": null,
        "madde_no": "55",
        "article": "55",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "4734",
          "rag_domain": "legal",
          "madde_no": "55",
          "source": "4734",
          "title": "Kamu İhale Kanunu (4734)",
          "trusted_source": true
        }
      },
      {
        "score": 0.51385796,
        "chunk_id": "77df74b5-a77d-5701-bbc2-c3d0c54961b5",
        "title": "Tüketicinin Korunması Hakkında Kanun (6502)",
        "text": "MADDE 69- (1) Tüketici hakem heyetleri uyuşmazlık konusuna ilişkin her türlü bilgi \nve belgeyi taraflardan, ilgili kurum veya kuruluşlardan isteyebilir.  \n \nKarar ve karara itiraz",
        "source": "6502",
        "rag_domain": "legal",
        "law_number": "6502",
        "document_id": null,
        "madde_no": "69",
        "article": "69",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "6502",
          "rag_domain": "legal",
          "madde_no": "69",
          "source": "6502",
          "title": "Tüketicinin Korunması Hakkında Kanun (6502)",
          "trusted_source": true
        }
      }
    ],
    "retrieval_score": 0.5687,
    "confidence_type": "retrieval_score",
    "llm": {
      "provider": "evren",
      "model": "llm-large"
    }
  }
}
```

**State'e yazılan tam çıktı:**

```json
{
  "required_fields": [
    "person_name",
    "address",
    "signature_present",
    "subject",
    "request"
  ],
  "present_fields": [
    "person_name",
    "address",
    "subject",
    "request"
  ],
  "missing_fields": [],
  "uncertain_fields": [
    "signature_present"
  ],
  "field_results": {
    "person_name": {
      "status": "present",
      "value": "Polat Madencilik adına Pelin Sönmez"
    },
    "address": {
      "status": "present",
      "value": "Örenli İlçe Kaymakamlığı"
    },
    "signature_present": {
      "status": "uncertain",
      "reason": "Unknown status."
    },
    "subject": {
      "status": "present",
      "value": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi"
    },
    "request": {
      "status": "present",
      "value": "idari inceleme talep ediyoruz"
    }
  },
  "legal_basis": [],
  "warnings": [],
  "needs_human_review": true
}
```
### summary_agent

**Tam tüketilen giriş:**

```json
{
  "raw_text": "ÖRENLİ İLÇE KAYMAKAMLIĞINA\n\nBAŞVURAN: Polat Madencilik adına Pelin Sönmez\n\nKONU: Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi\n\nAÇIKLAMALAR:\n1. Kurum araçları akaryakıt alımı ihalesinin idari şartnamesi ile sözleşme tasarısında ödeme vadelerine ilişkin birbiriyle çelişkili maddeler bulunmaktadır, idari inceleme talep ediyoruz.\n2. 4734 sayılı Kamu İhale Kanunu uyarınca gerekli yasal incelemenin yapılmasını talep ediyoruz.\n3. Gereğinin ivedilikle yapılmasını arz ederim.\n\nİmza: Polat Madencilik adına Pelin Sönmez",
  "document": {
    "document_type": "dilekce",
    "process_intent": "basvuru",
    "subject_excerpt": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
    "request_excerpt": "idari inceleme talep ediyoruz",
    "evidence": [
      {
        "field": "subject",
        "text": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi"
      },
      {
        "field": "request",
        "text": "idari inceleme talep ediyoruz"
      }
    ],
    "classification_mode": "llm",
    "evidence_mode": "llm",
    "needs_human_review": false,
    "priority": "HIGH",
    "priority_rule": "explicit_urgency",
    "priority_reason": "Evrak açık bir acil/ivedi işlem ifadesi içeriyor.",
    "deadline": null,
    "days_remaining": null,
    "decision_source": "rule_based",
    "raw_llm_result": {
      "document_type": "dilekce",
      "process_intent": "basvuru",
      "evidence": [
        {
          "field": "subject",
          "text": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi"
        },
        {
          "field": "request",
          "text": "idari inceleme talep ediyoruz"
        }
      ]
    },
    "llm": {
      "provider": "evren",
      "model": "llm-fast"
    }
  },
  "extraction.fields": {
    "signature_present": {
      "value": null,
      "status": "unknown",
      "evidence": null,
      "source": "document",
      "method": "deterministic",
      "validated": true
    },
    "authority_document_present": {
      "value": null,
      "status": "unknown",
      "evidence": null,
      "source": "document",
      "method": "deterministic",
      "validated": true
    },
    "subject": {
      "value": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
      "evidence": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
      "source": "document",
      "method": "document_agent",
      "validated": true
    },
    "request": {
      "value": "idari inceleme talep ediyoruz",
      "evidence": "idari inceleme talep ediyoruz",
      "source": "document",
      "method": "document_agent",
      "validated": true
    },
    "person_name": {
      "value": "Polat Madencilik adına Pelin Sönmez",
      "evidence": "BAŞVURAN: Polat Madencilik adına Pelin Sönmez",
      "source": "document",
      "method": "deterministic",
      "validated": true
    },
    "address": {
      "value": "Örenli İlçe Kaymakamlığı",
      "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA",
      "source": "document",
      "method": "llm",
      "validated": true
    },
    "institution": {
      "value": "Örenli İlçe Kaymakamlığı",
      "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA",
      "source": "document",
      "method": "llm",
      "validated": true
    },
    "sender_unit": {
      "value": "Polat Madencilik",
      "evidence": "Polat Madencilik",
      "source": "document",
      "method": "llm",
      "validated": true
    },
    "recipient": {
      "value": "Örenli İlçe Kaymakamlığı",
      "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA",
      "source": "document",
      "method": "llm",
      "validated": true
    },
    "other_entities": {
      "value": [
        {
          "type": "organization",
          "value": "Polat Madencilik",
          "evidence": "Polat Madencilik"
        },
        {
          "type": "organization",
          "value": "Polat Madencilik",
          "evidence": "Polat Madencilik"
        }
      ],
      "evidence": [
        "Polat Madencilik",
        "Polat Madencilik"
      ],
      "source": "document",
      "method": "llm",
      "validated": true
    }
  }
}
```

**State'e yazılan tam çıktı:**

```json
{
  "short_summary": "Polat Madencilik adına Pelin Sönmez tarafından Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi konusunda başvuru yapılmıştır. Başvuruda idari inceleme talep ediyoruz talep edilmektedir.",
  "summary_mode": "deterministic",
  "structured_summary": {
    "applicant": "Polat Madencilik adına Pelin Sönmez",
    "subject": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
    "request": "idari inceleme talep ediyoruz",
    "important_dates": [],
    "important_entities": [
      "Örenli İlçe Kaymakamlığı"
    ]
  },
  "source_map": {
    "applicant": "extraction.fields.person_name",
    "subject": "extraction.fields.subject",
    "request": "extraction.fields.request",
    "important_entities": "extraction.fields.institution",
    "short_summary": "deterministic_template"
  },
  "warnings": [],
  "needs_human_review": false,
  "llm": {
    "provider": "evren",
    "model": "llm-fast",
    "attempted": false,
    "status": "not_required",
    "error": null
  }
}
```
### routing_agent

**Tam tüketilen giriş:**

```json
{
  "document.document_type": "dilekce",
  "document.process_intent": "basvuru",
  "document.subject_excerpt": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
  "document.request_excerpt": "idari inceleme talep ediyoruz",
  "extraction.fields": {
    "signature_present": {
      "value": null,
      "status": "unknown",
      "evidence": null,
      "source": "document",
      "method": "deterministic",
      "validated": true
    },
    "authority_document_present": {
      "value": null,
      "status": "unknown",
      "evidence": null,
      "source": "document",
      "method": "deterministic",
      "validated": true
    },
    "subject": {
      "value": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
      "evidence": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
      "source": "document",
      "method": "document_agent",
      "validated": true
    },
    "request": {
      "value": "idari inceleme talep ediyoruz",
      "evidence": "idari inceleme talep ediyoruz",
      "source": "document",
      "method": "document_agent",
      "validated": true
    },
    "person_name": {
      "value": "Polat Madencilik adına Pelin Sönmez",
      "evidence": "BAŞVURAN: Polat Madencilik adına Pelin Sönmez",
      "source": "document",
      "method": "deterministic",
      "validated": true
    },
    "address": {
      "value": "Örenli İlçe Kaymakamlığı",
      "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA",
      "source": "document",
      "method": "llm",
      "validated": true
    },
    "institution": {
      "value": "Örenli İlçe Kaymakamlığı",
      "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA",
      "source": "document",
      "method": "llm",
      "validated": true
    },
    "sender_unit": {
      "value": "Polat Madencilik",
      "evidence": "Polat Madencilik",
      "source": "document",
      "method": "llm",
      "validated": true
    },
    "recipient": {
      "value": "Örenli İlçe Kaymakamlığı",
      "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA",
      "source": "document",
      "method": "llm",
      "validated": true
    },
    "other_entities": {
      "value": [
        {
          "type": "organization",
          "value": "Polat Madencilik",
          "evidence": "Polat Madencilik"
        },
        {
          "type": "organization",
          "value": "Polat Madencilik",
          "evidence": "Polat Madencilik"
        }
      ],
      "evidence": [
        "Polat Madencilik",
        "Polat Madencilik"
      ],
      "source": "document",
      "method": "llm",
      "validated": true
    }
  }
}
```

**State'e yazılan tam çıktı:**

```json
{
  "recommended_unit": null,
  "alternative_units": [
    "İlçe Nüfus Müdürlüğü",
    "Sosyal Yardımlaşma ve Dayanışma Vakfı (SYDV)"
  ],
  "ranked_units": [
    {
      "unit_id": "yazi_isleri",
      "name": "Yazı İşleri Müdürlüğü",
      "score": 50
    },
    {
      "unit_id": "nufus",
      "name": "İlçe Nüfus Müdürlüğü",
      "score": 50
    },
    {
      "unit_id": "sydv",
      "name": "Sosyal Yardımlaşma ve Dayanışma Vakfı (SYDV)",
      "score": 50
    }
  ],
  "reason": "Birden fazla birim eşit derecede olası veya yeterli kanıt yok.",
  "evidence": [],
  "routing_score": 0,
  "score_type": "rule_match",
  "score_breakdown": {
    "intent_score": 0,
    "keyword_score": 0,
    "doc_type_score": 0,
    "details": []
  },
  "registry_source": "data/institutions/kaymakamlik/kurum_profili_kaymakamlik.yaml",
  "needs_human_review": true,
  "warnings": [
    "Yönlendirme skoru düşük veya birimler arası fark çok az. Yanlış birim atamamak için manuel inceleme önerilir."
  ],
  "routing_confidence_type": "rule_margin"
}
```
### writing_agent

**Tam tüketilen giriş:**

```json
{
  "document_summary": "Polat Madencilik adına Pelin Sönmez tarafından Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi konusunda başvuru yapılmıştır. Başvuruda idari inceleme talep ediyoruz talep edilmektedir.",
  "requested_action": "basvuru",
  "missing_fields": [],
  "verified_facts": [
    "İşlem Türü: basvuru"
  ],
  "recipient": "Örenli İlçe Kaymakamlığı",
  "sender_unit": null,
  "state": {
    "extraction": {
      "fields": {
        "signature_present": {
          "value": null,
          "status": "unknown",
          "evidence": null,
          "source": "document",
          "method": "deterministic",
          "validated": true
        },
        "authority_document_present": {
          "value": null,
          "status": "unknown",
          "evidence": null,
          "source": "document",
          "method": "deterministic",
          "validated": true
        },
        "subject": {
          "value": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
          "evidence": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
          "source": "document",
          "method": "document_agent",
          "validated": true
        },
        "request": {
          "value": "idari inceleme talep ediyoruz",
          "evidence": "idari inceleme talep ediyoruz",
          "source": "document",
          "method": "document_agent",
          "validated": true
        },
        "person_name": {
          "value": "Polat Madencilik adına Pelin Sönmez",
          "evidence": "BAŞVURAN: Polat Madencilik adına Pelin Sönmez",
          "source": "document",
          "method": "deterministic",
          "validated": true
        },
        "address": {
          "value": "Örenli İlçe Kaymakamlığı",
          "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA",
          "source": "document",
          "method": "llm",
          "validated": true
        },
        "institution": {
          "value": "Örenli İlçe Kaymakamlığı",
          "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA",
          "source": "document",
          "method": "llm",
          "validated": true
        },
        "sender_unit": {
          "value": "Polat Madencilik",
          "evidence": "Polat Madencilik",
          "source": "document",
          "method": "llm",
          "validated": true
        },
        "recipient": {
          "value": "Örenli İlçe Kaymakamlığı",
          "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA",
          "source": "document",
          "method": "llm",
          "validated": true
        },
        "other_entities": {
          "value": [
            {
              "type": "organization",
              "value": "Polat Madencilik",
              "evidence": "Polat Madencilik"
            },
            {
              "type": "organization",
              "value": "Polat Madencilik",
              "evidence": "Polat Madencilik"
            }
          ],
          "evidence": [
            "Polat Madencilik",
            "Polat Madencilik"
          ],
          "source": "document",
          "method": "llm",
          "validated": true
        }
      },
      "warnings": [],
      "needs_human_review": false,
      "llm": {
        "provider": "evren",
        "model": "llm-fast"
      }
    },
    "routing": {
      "recommended_unit": null,
      "alternative_units": [
        "İlçe Nüfus Müdürlüğü",
        "Sosyal Yardımlaşma ve Dayanışma Vakfı (SYDV)"
      ],
      "ranked_units": [
        {
          "unit_id": "yazi_isleri",
          "name": "Yazı İşleri Müdürlüğü",
          "score": 50
        },
        {
          "unit_id": "nufus",
          "name": "İlçe Nüfus Müdürlüğü",
          "score": 50
        },
        {
          "unit_id": "sydv",
          "name": "Sosyal Yardımlaşma ve Dayanışma Vakfı (SYDV)",
          "score": 50
        }
      ],
      "reason": "Birden fazla birim eşit derecede olası veya yeterli kanıt yok.",
      "evidence": [],
      "routing_score": 0,
      "score_type": "rule_match",
      "score_breakdown": {
        "intent_score": 0,
        "keyword_score": 0,
        "doc_type_score": 0,
        "details": []
      },
      "registry_source": "data/institutions/kaymakamlik/kurum_profili_kaymakamlik.yaml",
      "needs_human_review": true,
      "warnings": [
        "Yönlendirme skoru düşük veya birimler arası fark çok az. Yanlış birim atamamak için manuel inceleme önerilir."
      ],
      "routing_confidence_type": "rule_margin"
    },
    "kurum_profili_id": "kaymakamlik",
    "muhatap": null,
    "muhatap_turu": null
  }
}
```

**State'e yazılan tam çıktı:**

```json
{
  "draft_type": "cevap_yazisi",
  "draft_type_reason": "Başvuru sahibinin talebine (idari inceleme) doğrudan yanıt vermek amacıyla hazırlanacak resmi yazıdır.",
  "draft_generation_mode": "llm",
  "draft": {
    "sender_unit": null,
    "recipient": "Örenli İlçe Kaymakamlığı",
    "subject": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi Başvurusu Hk.",
    "body": "Örenli İlçe Kaymakamlığına,\n\nPolat Madencilik adına Pelin Sönmez tarafından Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi konusunda yapılan ve idari inceleme talep edilen başvurunuz incelenmiştir.\n\nBaşvurunuzun işleme alınmış olduğu bilgilerini rica ederim.",
    "closing": null
  },
  "rendered_text": "Örenli İlçe Kaymakamlığı\n\nKonu: Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi Başvurusu Hk.\n\nÖrenli İlçe Kaymakamlığına,\n\nPolat Madencilik adına Pelin Sönmez tarafından Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi konusunda yapılan ve idari inceleme talep edilen başvurunuz incelenmiştir.\n\nBaşvurunuzun işleme alınmış olduğu bilgilerini rica ederim.",
  "official_render": {
    "attempted": true,
    "success": true,
    "template": "cevap_yazisi.jinja2",
    "missing_fields": [
      "tc_baslik.birim_adi",
      "sayi",
      "tarih",
      "ilgi",
      "imza.ad_soyad",
      "imza.unvan"
    ],
    "warnings": [
      "Muhatap kurum hiyerarşisi bilinmiyor; canonical üst makam fallback kapanışı kullanıldı.",
      "Taslak önizlemesinde eksik alanlar açık placeholder olarak gösterildi; personel/EBYS tarafından tamamlanmalıdır."
    ],
    "source_map": {
      "tc_baslik.idare_adi": "institution_profile.kurum_adi",
      "sayi": "placeholder: outgoing EBYS metadata unavailable",
      "tarih": "placeholder: outgoing EBYS metadata unavailable",
      "konu": "extraction.fields.subject.value",
      "muhatap": "extraction.fields.recipient.value",
      "kapalis_ifadesi": "derived_from_context.muhatap_turu",
      "metin_paragraflari": "draft.body",
      "imza.ad_soyad": "placeholder: signer unavailable",
      "imza.unvan": "placeholder: signer title unavailable"
    },
    "fallback_policies": {
      "muhatap_turu": "unknown_hierarchy_as_kurum_ust"
    },
    "context": {
      "tc_baslik": {
        "idare_adi": "ÖRENLI İLÇE KAYMAKAMLIĞI",
        "birim_adi": "[BİRİM ADI]"
      },
      "sayi": "[SAYI]",
      "tarih": "[TARİH]",
      "konu": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
      "muhatap": {
        "tur": "kurum",
        "isim": "ÖRENLI İLÇE KAYMAKAMLIĞI"
      },
      "muhatap_turu": "kurum_ust",
      "kapalis_ifadesi": "arz ederim.",
      "ilgi": [
        {
          "tarih": "[İLGİ TARİHİ]",
          "sayi": "[İLGİ SAYISI]",
          "aciklama": "ilgi yazınız"
        }
      ],
      "metin_paragraflari": [
        "Örenli İlçe Kaymakamlığına,",
        "Polat Madencilik adına Pelin Sönmez tarafından Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi konusunda yapılan ve idari inceleme talep edilen başvurunuz incelenmiştir.",
        "Başvurunuzun işleme alınmış olduğu bilgilerini rica ederim."
      ],
      "imza": {
        "ad_soyad": "[AD SOYAD]",
        "unvan": "[UNVAN]",
        "yetki_turu": "normal"
      },
      "ekler": [],
      "dagitim": null,
      "iletisim": {
        "adres": "",
        "irtibat": ""
      },
      "sayfa_no": null,
      "uygunsuz_belge_uyarisi": null
    }
  },
  "official_rendered_text": "\n\n\n\n\nT.C.\nÖRENLI İLÇE KAYMAKAMLIĞI\n[BİRİM ADI]\n\n\n\nSayı: [SAYI]                                                                    Tarih: [TARİH]\n\n\nKonu: Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi\n\n\n\n                              ÖRENLI İLÇE KAYMAKAMLIĞI\n\n\n\n\n\n\nİlgi: [İLGİ TARİHİ] tarihli ve [İLGİ SAYISI] sayılı ilgi yazınız.\n\n\n\n\n\n\n\n\n\n\n\n\tÖrenli İlçe Kaymakamlığına,\n\tPolat Madencilik adına Pelin Sönmez tarafından Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi konusunda yapılan ve idari inceleme talep edilen başvurunuz incelenmiştir.\n\tBaşvurunuzun işleme alınmış olduğu bilgilerini rica ederim.\n\n\n\narz ederim.\n\n\n\n                                    [AD SOYAD]\n                                    [UNVAN]\n\n\n\n\nEk konulmadı.\n\n\n\n\n\n\n\n________________________________________________________________________________\n                                                                                \n",
  "process_explanation": "Sistem evrakın içeriğine göre cevap yazısı hazırlanmasını önerdi. Oluşturulan taslak nihai işlemden önce yetkili personelin onayına sunulmalıdır.",
  "applied_rules": [],
  "supporting_rules": [
    {
      "evidence": "Tekit yazıları amacı itibarıyla hiyerarşi yönünden alt veya aynı düzey idarelere yazılmalıdır.",
      "source": "K2"
    },
    {
      "evidence": "sayılı ...” ibaresi kullanılır ve ilginin sonuna nokta (.)",
      "source": "K5"
    },
    {
      "evidence": "istendiğinde, ilgi bölümü “İsimsiz ve tarihsiz başvuru/dilekçe.” biçiminde yazılır.",
      "source": "K5"
    }
  ],
  "rule_validation": {
    "proposed": 0,
    "validated": 0
  },
  "sources": [
    {
      "score": 0.5834862,
      "chunk_id": "7cf2efd7-5396-5d4d-a399-5388fdaa6530",
      "title": "Resmî Yazışmalar Kılavuzu",
      "text": "iyle bitirilmelidir. (Örneğin; Teftiş Kurulu Başkanlığı – Personel Genel Müdürlüğü\nvb.) \nMuhatap kısmında ikinci satırda parantez içinde birim veya idare ismi belirtilen yazışmalar, birinci\nsatırda yer alan muhatap idare dikkate alınarak arz veya rica ibarelerinden uygun olanı ile\nbitirilmelidir:\nMuhatapta Parantez Kullanımı\n  ÇEVRE, ŞEHİRCİLİK VE İKLİM DEĞİŞİKLİĞİ BAKANLIĞINA\n  (Toplu Konut İdaresi Başkanlığı)\n  \n  HAZİNE VE MALİYE BAKANLIĞINA\n  (Muhasebat Genel Müdürlüğü)\n  \nAçıklama\nMetin kısmında arz veya rica durumu belgeyi\nimzalayan \nkişiye \nve \ngönderilecek \nidare\nbilgisinde yer alan  “Çevre, Şehircilik ve İklim\nDeğişikliği Bakanlığına” göre belirlenir.\nMetin kısmında arz veya rica durumu belgeyi\nimzalayan \nkişiye \nve \ngönderilecek \nidare\nbilgisinde yer alan  “Hazine ve Maliye\nBakanlığına” göre belirlenir.\nResmî yazışmaların metin sonunda kullanılan “arz” ve “rica” ibarelerinin belirlenmesinde muhatap\nidare üst yöneticisinin ek göstergesinin, protokolün ve hiyerarşinin esas alınması gibi idarelerce\ngeliştirilen yanlış yöntemler ve süreçler bulunmaktadır. “Arz” ve “rica” ibarelerinin tercih edilmesinde\nmevzuatla hiyerarşi yönünden ast-üst ilişkisinin tanımlanmadığı durumlarda metin sonunun “arz\nederim” ifadesi ile bitirilmesi uygun olacaktır. Böylelikle söz konusu ifade, resmî yazı içeriğinin önüne\ngeçmeyerek iş ve işlemlerin hızlıca yürütülmesi sağlanmış olacaktır. Örneğin; Cumhurbaşkanlığına\nbağlı  kurum ve  kuruluşlar ile bakanlıklar arasında yapılacak yazışmalara ai",
      "source": "resmi_yazisma_kilavuzu",
      "rag_domain": "official_writing",
      "law_number": "resmi_yazisma_kilavuzu",
      "document_id": null,
      "madde_no": "CHUNK_30",
      "article": "CHUNK_30",
      "trusted_source": true,
      "metadata": {
        "rag_eligible": true,
        "law_number": "resmi_yazisma_kilavuzu",
        "rag_domain": "official_writing",
        "madde_no": "CHUNK_30",
        "source": "resmi_yazisma_kilavuzu",
        "title": "Resmî Yazışmalar Kılavuzu",
        "trusted_source": true
      }
    },
    {
      "score": 0.5753081,
      "chunk_id": "f0244dd0-7f6e-51e7-ba71-fdb5a6be6092",
      "title": "Resmî Yazışmalar Kılavuzu",
      "text": "anımlayıcı bilgilerle birlikte\nbelgenin muhatabı olunmadığı bilgisi, resmî yazıyla gönderen idareye iletilmelidir.\nİdareye muhatabı olmadığı hâlde fiziksel ortamda belge gelmesi durumunda:\nAsıl muhatabı anlaşılamıyorsa belge gönderene iade edilmelidir.\nAsıl muhatabın açıkça belli olması durumunda, belgenin bir sureti alınarak aslı muhatabına\ngönderilmeli ve belgeyi gönderene de bilgi verilmelidir.\n\n95\n30. TEKİT YAZISI\nYönetmelik 34. Madde\nBelgeye süresi içinde cevap verilmemesi durumunda muhataba tekit yazısı yazılabilmektedir.\nTekit yazıları amacı itibarıyla hiyerarşi yönünden alt veya aynı düzey idarelere yazılmalıdır.\nKurumlar hiyerarşi yönünden üst seviyedeki kurumlara tekit yazısı yazmamalıdır.\nTekit yazısında daha önce gönderilen belge ilgi olarak tutulmalıdır.\nTekit Yazısı Örneği\nTekit \nyazısında \ndaha \nönce\ngönderilen yazının ilgi tutulması\nzorunludur.\n\n96\n31. UYGUN YAZILMAYAN BELGELER\nYönetmelik 35. Madde\nResmî yazışmalarda uygulama birliğinin sağlanması amacıyla idareler tarafından hazırlanan veya\nteslim alınan belgeler Yönetmelik’e uygunluk açısından incelenmelidir. Herhangi bir madde hükmüne\naykırı hazırlanan bir belge teslim alındığında muhatap cevabî yazıda veya şifahen uyarılmalı,\nYönetmelik’e aykırılığın daha sonra gerçekleştirilen yazışmalarda da devam etmesi durumunda ise\naşağıda örneği verilen yazıyla muhatap uyarılmalıdır: \nMUHATAP \ngg.aa.yyyy tarihli ve …-..….-…..-….. sayılı yazınız Resmî Yazışmalarda Uygulanacak Usul ve\nEsaslar Hakkında Yönetmelik’in  ……",
      "source": "resmi_yazisma_kilavuzu",
      "rag_domain": "official_writing",
      "law_number": "resmi_yazisma_kilavuzu",
      "document_id": null,
      "madde_no": "CHUNK_83",
      "article": "CHUNK_83",
      "trusted_source": true,
      "metadata": {
        "rag_eligible": true,
        "law_number": "resmi_yazisma_kilavuzu",
        "rag_domain": "official_writing",
        "madde_no": "CHUNK_83",
        "source": "resmi_yazisma_kilavuzu",
        "title": "Resmî Yazışmalar Kılavuzu",
        "trusted_source": true
      }
    },
    {
      "score": 0.57397354,
      "chunk_id": "3a37a213-8c8c-51ee-bf18-51a3b970ba65",
      "title": "Resmî Yazışmalar Kılavuzu",
      "text": "len tarih bilgisine ilgide muhakkak yer verilmelidir.\nYanlış Kullanım\nBila tarihli ve E-84801842-902.02-1042582 sayılı\nyazınız.\nDoğru Kullanım\n01.09.2019 \ntarihli \nve \nE-84801842-902.02-\n1042582 sayılı yazınız.\n\nYanlış Kullanım\n01.09.2019 tarihli ve 1042582 sayılı yazımız.\nDoğru Kullanım\n01.09.2019 \ntarihli \nve \nE-84801842-902.02-\n1042582 sayılı yazımız.\n12.3. İlgi Tutulan Belge Sayısının Yazımı \nİlgi olarak eklenen belgenin sadece kayıt numarası yazılmamalı, belgenin hazırlanma süreci ve ait\nolduğu idare/birim bilgisine de erişilebilmesi amacıyla 4 bölümden oluşan sayı, bütünüyle\nyazılmalıdır.\n28\n\n29\nİlgi tutulan belge bilgilerinin\n(tarih, sayı ve geldiği idare)\nyazılması gerekmektedir. \nMetin kısmında ilk paragrafta ilgi\ntutulan belgenin içeriği hakkında\nbilgi \nverilerek \nilgi \nile \nbelge\narasında bağ kurulmalıdır.\nİlgide \nyer \nalan \nbelge \nmuhatap\nkurumda bulunmayan bir belge ise ek\nolarak gönderilmesi uygun olacaktır.\nİlgi \ntutulan \nbelge \nkurumların\nrahatlıkla Resmî Gazete üzerinden\nulaşabileceği kanun, yönetmelik vb.\nise \nayrıca \ngönderilmesine \ngerek\nyoktur. \n\n13. METİN\nYönetmelik 16. Madde\nResmî yazılarda esas unsuru teşkil eden ve muhatabın bilgilendirildiği kısım metindir. Metin,\naşağıdaki hususlar dikkate alınarak hazırlanmalıdır:\nAçık, anlaşılabilir, kısa ve olabildiğince öz anlatım benimsenmeli,\nHerkesçe bilinen Türkçe kelimeler tercih edilmeli,\nTürkçe dil bilgisi ve yazım kurallarına uygunluk sağlanmalı (Türk Dil Kurumu Sözlüğü ve Yazım\nKılavuzu dikkate alınmalı",
      "source": "resmi_yazisma_kilavuzu",
      "rag_domain": "official_writing",
      "law_number": "resmi_yazisma_kilavuzu",
      "document_id": null,
      "madde_no": "CHUNK_28",
      "article": "CHUNK_28",
      "trusted_source": true,
      "metadata": {
        "rag_eligible": true,
        "law_number": "resmi_yazisma_kilavuzu",
        "rag_domain": "official_writing",
        "madde_no": "CHUNK_28",
        "source": "resmi_yazisma_kilavuzu",
        "title": "Resmî Yazışmalar Kılavuzu",
        "trusted_source": true
      }
    },
    {
      "score": 0.57000995,
      "chunk_id": "e4a52b71-d415-53c5-81b6-2642a25a52ca",
      "title": "Resmî Yazışmalar Kılavuzu",
      "text": "re ismi yer almalıdır. Ayrıca farklı idarelerde\naynı birim adı olabileceğinden karışıklığa yol\naçmaması adına idare ismi kullanılmalıdır.\n26\n\n12. İLGİ\n27\nYönetmelik 15. Madde\nİlgi, iki yana yaslı olarak yazılan ve birden fazla olduğunda belgelerin tarih sırasına göre kronolojik\ndüzenlendiği alandır. İlgide aşağıdaki bilgilerin yer alması gerekmektedir.\n12.1.  İlgi Tutulan Belgenin Sahibi İdarenin Yazımı\nİlgi Kullanımı\nTicaret Bakanlığının (Personel Genel Müdürlüğü)\n01.09.2019 \ntarihli \nve \nE-35799330-902.02-\n1042579 sayılı yazısı.\nAçıklama\nİdare \ndışına \ngönderilen \nbelgelerde, \nsadece\n“Personel Genel Müdürlüğünün … tarihli ve ...\nsayılı yazısı” yazıldığı takdirde, belge sahibinin\nhangi idare olduğu anlaşılamayacağından idare\nisminin \n(Ticaret \nBakanlığı) \nyazılması\ngerekmektedir.\nYanlış Kullanım\nStrateji Geliştirme Daire Başkanlığının 01.09.2019\ntarihli E-84801842-902.02-1042580 sayılı yazısı.\nDoğru Kullanım\nAfyon Kocatepe Üniversitesi Rektörlüğünün\n(Strateji Geliştirme Daire Başkanlığı) 01.09.2019\ntarihli ve E-84801842-902.02-1042580 sayılı\nyazısı.\nİlgi tutulan belgelerden yazı içinde bahsedilmelidir. İlgi tutulan belgenin muhatapta olmaması\ndurumunda, belge muhataba ek olarak iletilmelidir.\nİlgi tutulan belge, Resmî Gazete’de yayımlanan bir mevzuat ise ayrıca ek olarak eklenmemelidir. \n12.2. İlgi Tutulan Belge Tarihinin Yazımı\nİlgi kısmında vatandaş başvuruları haricinde “bila tarihli” veya “tarihsiz” ifadesi kullanılmamalıdır.\nBelgenin görüntüsünden ve üstverisinden erişi",
      "source": "resmi_yazisma_kilavuzu",
      "rag_domain": "official_writing",
      "law_number": "resmi_yazisma_kilavuzu",
      "document_id": null,
      "madde_no": "CHUNK_27",
      "article": "CHUNK_27",
      "trusted_source": true,
      "metadata": {
        "rag_eligible": true,
        "law_number": "resmi_yazisma_kilavuzu",
        "rag_domain": "official_writing",
        "madde_no": "CHUNK_27",
        "source": "resmi_yazisma_kilavuzu",
        "title": "Resmî Yazışmalar Kılavuzu",
        "trusted_source": true
      }
    },
    {
      "score": 0.5577692,
      "chunk_id": "fe42ad7a-7fed-51b2-a9d9-2edc45d3088b",
      "title": "Resmî Yazışmalarda Uygulanacak Usul ve Esaslar Hakkında Yönetmelik",
      "text": "MADDE 15- (1) İlgi, belgenin bağlantılı olduğu diğer belge veya belgelerin\nbelirtildiği bölümdür.\n\n(2) “İlgi:” yan başlığı, muhatap bölümünün son satırından itibaren iki satır boşluk\nbırakılarak ve yazı alanının solundan başlanarak yazılır (Örnek 7).\n\n(3) “Sayı”, “Konu” ve “İlgi” yan başlıklarından sonra kullanılan iki nokta\naynı hizada yazılır (Örnek 7).\n\n(4) İlgide yer alan bilgiler bir satırı geçerse, devamı “İlgi:” yan başlığının ve\nsıralamayı gösteren harflerin altı boş bırakılarak alt satıra yazılır (Örnek 7).\n\n(5) İlginin birden fazla olması durumunda, belgeler önceki tarihli olandan\nbaşlanarak tarih sırasına göre sıralanır. Sıralamada, Türk alfabesinde yer alan bütün küçük\nharfler, kendilerinden sonra kapama parantez işareti “)” konularak kullanılır (Örnek 7).\n\n(6) İlgide, ilgi tutulan belgeyi gönderen idarenin adı ile belgenin tarihi ve sayısı\nbelirtilir. Ancak ilgi tutulan belgenin, muhatap idarenin daha önce gönderdiği bir belge\nveya muhatap idareye daha önce gönderilen bir belge olması durumunda idare adı\nbelirtilmez (Örnek 7).\n\n(7) İlgide, “... tarihli ve ... sayılı ...” ibaresi kullanılır ve ilginin sonuna nokta (.)\nişareti konulur (Örnek 7).\n\n(8) İlgide belirtilen belge, muhatapta bulunmadığı durumlarda söz konusu belge, ek\nolarak muhatabına iletilebilir (Örnek 7).\n\n(9) İlgide belirtilen belge, gerçek kişiden geliyorsa ilgi bölümü “...ın ... tarihli\nbaşvurusu/dilekçesi.” biçiminde yazılır (Örnek 9). Ancak belgenin muhatabı, ilgi tutulan\nbaşvurunun veya dilekçenin sahibi ise ilgi bölümünde gerçek kişinin isim bilgisine yer\nverilmez.\n\n(10) Gerçek kişi ve tarih bilgisi bulunmayan başvuru/dilekçe ilgi tutulmak\nistendiğinde, ilgi bölümü “İsimsiz ve tarihsiz başvuru/dilekçe.” biçiminde yazılır. Söz\nkonusu başvurunun/dilekçenin işleme alınıp alınmayacağı ilgili mevzuat hükümlerine göre\ndeğerlendirilir.\n\n«>\n\nişareti\n\n«\n\nMetin",
      "source": "resmi_yazisma_yonetmeligi",
      "rag_domain": "official_writing",
      "law_number": "resmi_yazisma_yonetmeligi",
      "document_id": null,
      "madde_no": "15",
      "article": "15",
      "trusted_source": true,
      "metadata": {
        "rag_eligible": true,
        "law_number": "resmi_yazisma_yonetmeligi",
        "rag_domain": "official_writing",
        "madde_no": "15",
        "source": "resmi_yazisma_yonetmeligi",
        "title": "Resmî Yazışmalarda Uygulanacak Usul ve Esaslar Hakkında Yönetmelik",
        "trusted_source": true
      }
    }
  ],
  "retrieval_score": 0.5835,
  "llm": {
    "provider": "evren",
    "model": "llm-fast"
  },
  "verified_facts_used": [
    "İşlem Türü: basvuru"
  ],
  "requires_human_approval": true,
  "needs_additional_context": false,
  "warning": null
}
```
### quality_agent

**Tam tüketilen giriş:**

```json
{
  "document": {
    "document_type": "dilekce",
    "process_intent": "basvuru",
    "subject_excerpt": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
    "request_excerpt": "idari inceleme talep ediyoruz",
    "evidence": [
      {
        "field": "subject",
        "text": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi"
      },
      {
        "field": "request",
        "text": "idari inceleme talep ediyoruz"
      }
    ],
    "classification_mode": "llm",
    "evidence_mode": "llm",
    "needs_human_review": false,
    "priority": "HIGH",
    "priority_rule": "explicit_urgency",
    "priority_reason": "Evrak açık bir acil/ivedi işlem ifadesi içeriyor.",
    "deadline": null,
    "days_remaining": null,
    "decision_source": "rule_based",
    "raw_llm_result": {
      "document_type": "dilekce",
      "process_intent": "basvuru",
      "evidence": [
        {
          "field": "subject",
          "text": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi"
        },
        {
          "field": "request",
          "text": "idari inceleme talep ediyoruz"
        }
      ]
    },
    "llm": {
      "provider": "evren",
      "model": "llm-fast"
    }
  },
  "extraction": {
    "fields": {
      "signature_present": {
        "value": null,
        "status": "unknown",
        "evidence": null,
        "source": "document",
        "method": "deterministic",
        "validated": true
      },
      "authority_document_present": {
        "value": null,
        "status": "unknown",
        "evidence": null,
        "source": "document",
        "method": "deterministic",
        "validated": true
      },
      "subject": {
        "value": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
        "evidence": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
        "source": "document",
        "method": "document_agent",
        "validated": true
      },
      "request": {
        "value": "idari inceleme talep ediyoruz",
        "evidence": "idari inceleme talep ediyoruz",
        "source": "document",
        "method": "document_agent",
        "validated": true
      },
      "person_name": {
        "value": "Polat Madencilik adına Pelin Sönmez",
        "evidence": "BAŞVURAN: Polat Madencilik adına Pelin Sönmez",
        "source": "document",
        "method": "deterministic",
        "validated": true
      },
      "address": {
        "value": "Örenli İlçe Kaymakamlığı",
        "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA",
        "source": "document",
        "method": "llm",
        "validated": true
      },
      "institution": {
        "value": "Örenli İlçe Kaymakamlığı",
        "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA",
        "source": "document",
        "method": "llm",
        "validated": true
      },
      "sender_unit": {
        "value": "Polat Madencilik",
        "evidence": "Polat Madencilik",
        "source": "document",
        "method": "llm",
        "validated": true
      },
      "recipient": {
        "value": "Örenli İlçe Kaymakamlığı",
        "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA",
        "source": "document",
        "method": "llm",
        "validated": true
      },
      "other_entities": {
        "value": [
          {
            "type": "organization",
            "value": "Polat Madencilik",
            "evidence": "Polat Madencilik"
          },
          {
            "type": "organization",
            "value": "Polat Madencilik",
            "evidence": "Polat Madencilik"
          }
        ],
        "evidence": [
          "Polat Madencilik",
          "Polat Madencilik"
        ],
        "source": "document",
        "method": "llm",
        "validated": true
      }
    },
    "warnings": [],
    "needs_human_review": false,
    "llm": {
      "provider": "evren",
      "model": "llm-fast"
    }
  },
  "legal_analysis": {
    "answer": "Sağlanan kaynaklarda soruya ilişkin doğrulanabilir bir bilgi çıkarılamadı.",
    "evidence": [],
    "sources": [
      {
        "score": 0.56865597,
        "chunk_id": "0c698c92-161c-500d-9a33-d275292f7c8a",
        "title": "Kamu İhale Kanunu (4734)",
        "text": "Madde 56- (Değişik: 22/11/2008-5812/23 md.) \nİdareye şikayet başvurusunda bulunan veya idarece alınan kararı uygun bulmayan aday, \nistekli veya istekli olabilecekler tarafından 55 inci maddenin dördüncü fıkrasında belirtilen \nhallerde ve sürede, sözleşme imzalanmadan önce itirazen şikayet başvurusunda bulunulabilir. \nİhalenin iptaline ilişkin işlem ve kararlardan, sadece şikayet ve itirazen şikayet üzerine alınanlar \nitirazen şikayete konu edilebilir ve bu kararlara karşı beş gün içinde doğrudan Kuruma başvuruda \nbulunulabilir. \nKurum itirazen şikayet başvurularını başvuru sahibinin iddiaları ile idarenin şikayet \nüzerine aldığı kararda belirlenen hususlar ve itiraz edilen işlemler bakımından eşit muamele \nilkesinin ihlal edilip edilmediği açılarından inceler. İdare tarafından şikayet veya itirazen şikayet \nüzerine alınan ihalenin iptal edilmesi işlemine karşı yapılacak itirazen şikayet başvuruları ise \nidarenin iptal gerekçeleriyle sınırlı incelenir. \nKanunda belirtilen sürelere ve usule uyulmadan sözleşme imzalanmış olması veya itirazen \nşikayet başvurusundan feragat edilmesi itirazen şikayet başvurusunun incelenmesine ve 54 üncü \nmaddede sayılan kararlardan birinin alınmasına engel teşkil etmez. \n \n60 20/11/2008 tarihli ve 5812 sayılı Kanunun 23 üncü maddesiyle bu madde başlığı “Kamu İhale Kurulu \ntarafından inceleme” iken, 5/1/2009 tarihinden geçerli olmak üzere metne işlendiği şekilde \ndeğiştirilmiştir. \n\nKurul tarafından gerekli görülen hallerde tarafların ve ilgililerin dinlenmesine karar \nverilir. Bu durumda, Kurul tarafından tespit edilen tarihte taraflar ve ilgililer dinlenir. \nKurum, itirazen şikayete ilişkin nihai kararını, incelenen ihaleye ilişkin gerekli bilgi ve \nbelgeler ile ihale işlem dosyasının kayıtlara alındığı tarihi izleyen yirmi gün içinde vermek \nzorundadır. Bu süre 21 inci maddenin (b) ve (c) bentlerine göre yapılan ihaleler ile şikayet ve \nitirazen şikayet üzerine alınan ihalenin iptal edilmesi işlemine karşı yapılacak itirazen şikayet \nb",
        "source": "4734",
        "rag_domain": "legal",
        "law_number": "4734",
        "document_id": null,
        "madde_no": "56",
        "article": "56",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "4734",
          "rag_domain": "legal",
          "madde_no": "56",
          "source": "4734",
          "title": "Kamu İhale Kanunu (4734)",
          "trusted_source": true
        }
      },
      {
        "score": 0.5609256,
        "chunk_id": "1fffd493-df26-5842-910e-81bad6d09500",
        "title": "Kamu İhale Kanunu (4734)",
        "text": "Madde 54- (Değişik: 20/11/2008-5812/21 md.)  \nİhale sürecindeki hukuka aykırı işlem veya eylemler nedeniyle bir hak kaybına veya \nzarara uğradığını veya zarara uğramasının muhtemel olduğunu iddia eden aday veya istekli ile \nistekli olabilecekler, bu Kanunda belirtilen şekil ve usul kurallarına uygun olmak şartıyla şikayet \nve itirazen şikayet başvurusunda bulunabilirler. \nŞikayet ve itirazen şikayet başvuruları, dava açılmadan önce tüketilmesi zorunlu idari \nbaşvuru yollarıdır. \nŞikayet başvuruları idareye, itirazen şikayet başvuruları Kuruma hitaben yazılmış imzalı \ndilekçelerle yapılır.  \nDilekçelerde aşağıdaki hususlara yer verilir: \na) Başvuru sahibinin, varsa vekil ya da temsilcisinin adı, soyadı veya unvanı ve adresi. \nb) İhaleyi yapan idarenin ve ihalenin adı veya ihale kayıt numarası. \nc) Başvuruya konu olan durumun farkına varıldığı veya bildirildiği tarih. \nd) Başvurunun konusu, sebepleri ve dayandığı deliller. \ne) İtirazen şikayet başvurularında idareye yapılan şikayetin ve varsa şikayete ilişkin idare \nkararının bildirim tarihi. \n(Değişik beşinci fıkra:28/1/2021-7263/10 md.) Şikâyet ve itirazen şikâyet başvuru \ndilekçelerinde yer alması gereken diğer bilgiler ile bu dilekçelere eklenmesi gereken belgelere, \nbunların sunuluş şekli ile bu başvuruların elektronik ortamda yapılmasına ilişkin usul ve esasları \nbelirlemeye Kurum yetkilidir.  \nİtirazen şikayette bulunanlardan 53 üncü maddenin (j) bendinin (2) nolu alt bendinde \nbelirtilen bedelin dört katı tutarına kadar başvuru teminatı alınmasına Cumhurbaşkanınca karar \nverilebilir. Başvuru teminatları Kurum hesaplarına yatırılır. Bu teminatlar Kurum gelirleri ile \nilişkilendirilmeksizin ayrı hesaplarda tutulur.58 \n(Mülga yedinci fıkra:28/1/2021-7263/10 md.)  \nAynı kişi tarafından birden fazla ihaleye, birden fazla kişi tarafından ise aynı ihaleye tek \ndilekçe ile başvuruda bulunulamaz. \n(Ek: 6/2/2014-6518/50 md.) Başvuruların ihaleyi yapan idare veya Kurum dışındaki idari \n \n56 20/11/2008 tarihli ve 5812 say",
        "source": "4734",
        "rag_domain": "legal",
        "law_number": "4734",
        "document_id": null,
        "madde_no": "54",
        "article": "54",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "4734",
          "rag_domain": "legal",
          "madde_no": "54",
          "source": "4734",
          "title": "Kamu İhale Kanunu (4734)",
          "trusted_source": true
        }
      },
      {
        "score": 0.5538851,
        "chunk_id": "213251bd-4eeb-512f-af39-42ed2e69083f",
        "title": "Kamu İhale Kanunu (4734)",
        "text": "Madde 37- İhale komisyonunun talebi üzerine idare tekliflerin incelenmesi, \nkarşılaştırılması ve değerlendirilmesinde yararlanmak üzere net olmayan hususlarla ilgili \nisteklilerden yazılı olarak tekliflerini açıklamalarını isteyebilir. Ancak bu açıklama, hiçbir şekilde \nteklif fiyatında değişiklik yapılması veya ihale dokümanında yer alan şartlara uygun olmayan \ntekliflerin uygun hale getirilmesi amacıyla istenilmez ve yapılmaz.  \n(Değişik ikinci fıkra: 20/11/2008-5812/11 md.) Tekliflerin değerlendirilmesinde, \nöncelikle belgeleri eksik olduğu veya teklif mektubu ile geçici teminatı usulüne uygun olmadığı \n36 ncı maddeye göre ilk oturumda tespit edilen isteklilerin tekliflerinin değerlendirme dışı \nbırakılmasına karar verilir. Ancak, teklifin esasını değiştirecek nitelikte olmaması kaydıyla, \nbelgelerde bilgi eksikliği bulunması halinde idarece belirlenen sürede isteklilerden bu eksik \nbilgilerin tamamlanması yazılı olarak istenir. Belirlenen sürede bilgileri tamamlamayan istekliler \ndeğerlendirme dışı bırakılır ve geçici teminatları gelir kaydedilir. Bu ilk değerlendirme ve \nişlemler sonucunda belgeleri eksiksiz ve teklif mektubu ile geçici teminatı usulüne uygun olan \nisteklilerin tekliflerinin ayrıntılı değerlendirilmesine geçilir. Bu aşamada, isteklilerin ihale konusu \nişi yapabilme kapasitelerini belirleyen yeterlik kriterlerine ve tekliflerin ihale dokümanında \nbelirtilen şartlara uygun olup olmadığı ile birim fiyat teklif cetvellerinde aritmetik hata bulunup \nbulunmadığı incelenir. Uygun olmadığı belirlenen isteklilerin teklifleri ile birim fiyat teklif \ncetvellerinde aritmetik hata bulunan teklifler değerlendirme dışı bırakılır. \n(Mülga son fıkra: 20/11/2008-5812/11 md.) \n \n36 20/11/2008 tarihli ve 5812 sayılı Kanunun 10 uncu maddesiyle; bu fıkrada yer alan “teklif fiyatları \naçıklanır” ibaresi “teklif fiyatları ve yaklaşık maliyet tutarı açıklanır” şeklinde değiştirilmiştir. \n\n \nAşırı düşük teklifler",
        "source": "4734",
        "rag_domain": "legal",
        "law_number": "4734",
        "document_id": null,
        "madde_no": "37",
        "article": "37",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "4734",
          "rag_domain": "legal",
          "madde_no": "37",
          "source": "4734",
          "title": "Kamu İhale Kanunu (4734)",
          "trusted_source": true
        }
      }
    ],
    "retrieved_sources": [
      {
        "score": 0.56865597,
        "chunk_id": "0c698c92-161c-500d-9a33-d275292f7c8a",
        "title": "Kamu İhale Kanunu (4734)",
        "text": "Madde 56- (Değişik: 22/11/2008-5812/23 md.) \nİdareye şikayet başvurusunda bulunan veya idarece alınan kararı uygun bulmayan aday, \nistekli veya istekli olabilecekler tarafından 55 inci maddenin dördüncü fıkrasında belirtilen \nhallerde ve sürede, sözleşme imzalanmadan önce itirazen şikayet başvurusunda bulunulabilir. \nİhalenin iptaline ilişkin işlem ve kararlardan, sadece şikayet ve itirazen şikayet üzerine alınanlar \nitirazen şikayete konu edilebilir ve bu kararlara karşı beş gün içinde doğrudan Kuruma başvuruda \nbulunulabilir. \nKurum itirazen şikayet başvurularını başvuru sahibinin iddiaları ile idarenin şikayet \nüzerine aldığı kararda belirlenen hususlar ve itiraz edilen işlemler bakımından eşit muamele \nilkesinin ihlal edilip edilmediği açılarından inceler. İdare tarafından şikayet veya itirazen şikayet \nüzerine alınan ihalenin iptal edilmesi işlemine karşı yapılacak itirazen şikayet başvuruları ise \nidarenin iptal gerekçeleriyle sınırlı incelenir. \nKanunda belirtilen sürelere ve usule uyulmadan sözleşme imzalanmış olması veya itirazen \nşikayet başvurusundan feragat edilmesi itirazen şikayet başvurusunun incelenmesine ve 54 üncü \nmaddede sayılan kararlardan birinin alınmasına engel teşkil etmez. \n \n60 20/11/2008 tarihli ve 5812 sayılı Kanunun 23 üncü maddesiyle bu madde başlığı “Kamu İhale Kurulu \ntarafından inceleme” iken, 5/1/2009 tarihinden geçerli olmak üzere metne işlendiği şekilde \ndeğiştirilmiştir. \n\nKurul tarafından gerekli görülen hallerde tarafların ve ilgililerin dinlenmesine karar \nverilir. Bu durumda, Kurul tarafından tespit edilen tarihte taraflar ve ilgililer dinlenir. \nKurum, itirazen şikayete ilişkin nihai kararını, incelenen ihaleye ilişkin gerekli bilgi ve \nbelgeler ile ihale işlem dosyasının kayıtlara alındığı tarihi izleyen yirmi gün içinde vermek \nzorundadır. Bu süre 21 inci maddenin (b) ve (c) bentlerine göre yapılan ihaleler ile şikayet ve \nitirazen şikayet üzerine alınan ihalenin iptal edilmesi işlemine karşı yapılacak itirazen şikayet \nb",
        "source": "4734",
        "rag_domain": "legal",
        "law_number": "4734",
        "document_id": null,
        "madde_no": "56",
        "article": "56",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "4734",
          "rag_domain": "legal",
          "madde_no": "56",
          "source": "4734",
          "title": "Kamu İhale Kanunu (4734)",
          "trusted_source": true
        }
      },
      {
        "score": 0.5609256,
        "chunk_id": "1fffd493-df26-5842-910e-81bad6d09500",
        "title": "Kamu İhale Kanunu (4734)",
        "text": "Madde 54- (Değişik: 20/11/2008-5812/21 md.)  \nİhale sürecindeki hukuka aykırı işlem veya eylemler nedeniyle bir hak kaybına veya \nzarara uğradığını veya zarara uğramasının muhtemel olduğunu iddia eden aday veya istekli ile \nistekli olabilecekler, bu Kanunda belirtilen şekil ve usul kurallarına uygun olmak şartıyla şikayet \nve itirazen şikayet başvurusunda bulunabilirler. \nŞikayet ve itirazen şikayet başvuruları, dava açılmadan önce tüketilmesi zorunlu idari \nbaşvuru yollarıdır. \nŞikayet başvuruları idareye, itirazen şikayet başvuruları Kuruma hitaben yazılmış imzalı \ndilekçelerle yapılır.  \nDilekçelerde aşağıdaki hususlara yer verilir: \na) Başvuru sahibinin, varsa vekil ya da temsilcisinin adı, soyadı veya unvanı ve adresi. \nb) İhaleyi yapan idarenin ve ihalenin adı veya ihale kayıt numarası. \nc) Başvuruya konu olan durumun farkına varıldığı veya bildirildiği tarih. \nd) Başvurunun konusu, sebepleri ve dayandığı deliller. \ne) İtirazen şikayet başvurularında idareye yapılan şikayetin ve varsa şikayete ilişkin idare \nkararının bildirim tarihi. \n(Değişik beşinci fıkra:28/1/2021-7263/10 md.) Şikâyet ve itirazen şikâyet başvuru \ndilekçelerinde yer alması gereken diğer bilgiler ile bu dilekçelere eklenmesi gereken belgelere, \nbunların sunuluş şekli ile bu başvuruların elektronik ortamda yapılmasına ilişkin usul ve esasları \nbelirlemeye Kurum yetkilidir.  \nİtirazen şikayette bulunanlardan 53 üncü maddenin (j) bendinin (2) nolu alt bendinde \nbelirtilen bedelin dört katı tutarına kadar başvuru teminatı alınmasına Cumhurbaşkanınca karar \nverilebilir. Başvuru teminatları Kurum hesaplarına yatırılır. Bu teminatlar Kurum gelirleri ile \nilişkilendirilmeksizin ayrı hesaplarda tutulur.58 \n(Mülga yedinci fıkra:28/1/2021-7263/10 md.)  \nAynı kişi tarafından birden fazla ihaleye, birden fazla kişi tarafından ise aynı ihaleye tek \ndilekçe ile başvuruda bulunulamaz. \n(Ek: 6/2/2014-6518/50 md.) Başvuruların ihaleyi yapan idare veya Kurum dışındaki idari \n \n56 20/11/2008 tarihli ve 5812 say",
        "source": "4734",
        "rag_domain": "legal",
        "law_number": "4734",
        "document_id": null,
        "madde_no": "54",
        "article": "54",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "4734",
          "rag_domain": "legal",
          "madde_no": "54",
          "source": "4734",
          "title": "Kamu İhale Kanunu (4734)",
          "trusted_source": true
        }
      },
      {
        "score": 0.5538851,
        "chunk_id": "213251bd-4eeb-512f-af39-42ed2e69083f",
        "title": "Kamu İhale Kanunu (4734)",
        "text": "Madde 37- İhale komisyonunun talebi üzerine idare tekliflerin incelenmesi, \nkarşılaştırılması ve değerlendirilmesinde yararlanmak üzere net olmayan hususlarla ilgili \nisteklilerden yazılı olarak tekliflerini açıklamalarını isteyebilir. Ancak bu açıklama, hiçbir şekilde \nteklif fiyatında değişiklik yapılması veya ihale dokümanında yer alan şartlara uygun olmayan \ntekliflerin uygun hale getirilmesi amacıyla istenilmez ve yapılmaz.  \n(Değişik ikinci fıkra: 20/11/2008-5812/11 md.) Tekliflerin değerlendirilmesinde, \nöncelikle belgeleri eksik olduğu veya teklif mektubu ile geçici teminatı usulüne uygun olmadığı \n36 ncı maddeye göre ilk oturumda tespit edilen isteklilerin tekliflerinin değerlendirme dışı \nbırakılmasına karar verilir. Ancak, teklifin esasını değiştirecek nitelikte olmaması kaydıyla, \nbelgelerde bilgi eksikliği bulunması halinde idarece belirlenen sürede isteklilerden bu eksik \nbilgilerin tamamlanması yazılı olarak istenir. Belirlenen sürede bilgileri tamamlamayan istekliler \ndeğerlendirme dışı bırakılır ve geçici teminatları gelir kaydedilir. Bu ilk değerlendirme ve \nişlemler sonucunda belgeleri eksiksiz ve teklif mektubu ile geçici teminatı usulüne uygun olan \nisteklilerin tekliflerinin ayrıntılı değerlendirilmesine geçilir. Bu aşamada, isteklilerin ihale konusu \nişi yapabilme kapasitelerini belirleyen yeterlik kriterlerine ve tekliflerin ihale dokümanında \nbelirtilen şartlara uygun olup olmadığı ile birim fiyat teklif cetvellerinde aritmetik hata bulunup \nbulunmadığı incelenir. Uygun olmadığı belirlenen isteklilerin teklifleri ile birim fiyat teklif \ncetvellerinde aritmetik hata bulunan teklifler değerlendirme dışı bırakılır. \n(Mülga son fıkra: 20/11/2008-5812/11 md.) \n \n36 20/11/2008 tarihli ve 5812 sayılı Kanunun 10 uncu maddesiyle; bu fıkrada yer alan “teklif fiyatları \naçıklanır” ibaresi “teklif fiyatları ve yaklaşık maliyet tutarı açıklanır” şeklinde değiştirilmiştir. \n\n \nAşırı düşük teklifler",
        "source": "4734",
        "rag_domain": "legal",
        "law_number": "4734",
        "document_id": null,
        "madde_no": "37",
        "article": "37",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "4734",
          "rag_domain": "legal",
          "madde_no": "37",
          "source": "4734",
          "title": "Kamu İhale Kanunu (4734)",
          "trusted_source": true
        }
      },
      {
        "score": 0.5187256,
        "chunk_id": "a9dd4747-35f6-5168-a61b-174631ac25ef",
        "title": "Kamu İhale Kanunu (4734)",
        "text": "Madde 55- (Değişik: 20/11/2008-5812/22 md.) \nŞikayet başvurusu, ihale sürecindeki işlem veya eylemlerin hukuka aykırılığı iddiasıyla bu \nişlem veya eylemlerin farkına varıldığı veya farkına varılmış olması gereken tarihi izleyen \ngünden itibaren 21 inci maddenin (b) ve (c) bentlerine göre yapılan ihalelerde beş gün, diğer \nhallerde ise on gün içinde ve sözleşmenin imzalanmasından önce, ihaleyi yapan idareye yapılır. \nİlanda yer alan hususlara yönelik başvuruların süresi ilk ilan tarihinden, ön yeterlik veya ihale \ndokümanının ilana yansımayan diğer hükümlerine yönelik başvuruların süresi ise dokümanın \nsatın alındığı tarihte başlar. \nİlan, ön yeterlik veya ihale dokümanına ilişkin şikayetler birinci fıkradaki süreleri aşmamak \nüzere en geç ihale veya son başvuru tarihinden üç iş günü öncesine kadar yapılabilir. Bu yöndeki \nbaşvuruların idarelerce ihale veya son başvuru tarihinden önce sonuçlandırılması esastır. Şikayet \nüzerine yapılan incelemede tekliflerin hazırlanmasını veya işin gerçekleştirilmesini etkileyebilecek \nmaddi veya teknik hataların veya eksikliklerin bulunması ve idarece ihale dokümanında düzeltme \nyapılmasına karar verilmesi halinde, gerekli düzeltme yapılarak 29 uncu maddede belirtilen usule \n \n59 20/11/2008 tarihli ve 5812 sayılı Kanunun 21 inci maddesiyle bu madde başlığı “İdare tarafından \ninceleme” iken, metne işlendiği şekilde değiştirilmiştir. \n\ngöre son başvuru veya ihale tarihi bir defaya mahsus olmak üzere ertelenir. Ancak belirlenen maddi \nveya teknik hataların veya eksikliklerin ilanda da bulunması halinde 26 ncı maddeye göre işlem \ntesis edilir. \nİdare, şikayet başvurusu üzerine gerekli incelemeyi yaparak on gün içinde gerekçeli bir \nkarar alır. Alınan karar, şikayetçi ile diğer aday veya istekliler ile istekli olabileceklere karar \ntarihini izleyen üç gün içinde bildirilir. İlan ile ihale veya ön yeterlik dokümanına yönelik \nbaşvurular dışında istekli olabileceklere bildirim yapılmaz. \nBelirtilen süre içinde bir karar alınmaması durumu",
        "source": "4734",
        "rag_domain": "legal",
        "law_number": "4734",
        "document_id": null,
        "madde_no": "55",
        "article": "55",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "4734",
          "rag_domain": "legal",
          "madde_no": "55",
          "source": "4734",
          "title": "Kamu İhale Kanunu (4734)",
          "trusted_source": true
        }
      },
      {
        "score": 0.51385796,
        "chunk_id": "77df74b5-a77d-5701-bbc2-c3d0c54961b5",
        "title": "Tüketicinin Korunması Hakkında Kanun (6502)",
        "text": "MADDE 69- (1) Tüketici hakem heyetleri uyuşmazlık konusuna ilişkin her türlü bilgi \nve belgeyi taraflardan, ilgili kurum veya kuruluşlardan isteyebilir.  \n \nKarar ve karara itiraz",
        "source": "6502",
        "rag_domain": "legal",
        "law_number": "6502",
        "document_id": null,
        "madde_no": "69",
        "article": "69",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "6502",
          "rag_domain": "legal",
          "madde_no": "69",
          "source": "6502",
          "title": "Tüketicinin Korunması Hakkında Kanun (6502)",
          "trusted_source": true
        }
      }
    ],
    "retrieval_score": 0.5687,
    "confidence_type": "retrieval_score",
    "llm": {
      "provider": "evren",
      "model": "llm-large"
    }
  },
  "missing_fields": {
    "required_fields": [
      "person_name",
      "address",
      "signature_present",
      "subject",
      "request"
    ],
    "present_fields": [
      "person_name",
      "address",
      "subject",
      "request"
    ],
    "missing_fields": [],
    "uncertain_fields": [
      "signature_present"
    ],
    "field_results": {
      "person_name": {
        "status": "present",
        "value": "Polat Madencilik adına Pelin Sönmez"
      },
      "address": {
        "status": "present",
        "value": "Örenli İlçe Kaymakamlığı"
      },
      "signature_present": {
        "status": "uncertain",
        "reason": "Unknown status."
      },
      "subject": {
        "status": "present",
        "value": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi"
      },
      "request": {
        "status": "present",
        "value": "idari inceleme talep ediyoruz"
      }
    },
    "legal_basis": [],
    "warnings": [],
    "needs_human_review": true
  },
  "summary": {
    "short_summary": "Polat Madencilik adına Pelin Sönmez tarafından Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi konusunda başvuru yapılmıştır. Başvuruda idari inceleme talep ediyoruz talep edilmektedir.",
    "summary_mode": "deterministic",
    "structured_summary": {
      "applicant": "Polat Madencilik adına Pelin Sönmez",
      "subject": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
      "request": "idari inceleme talep ediyoruz",
      "important_dates": [],
      "important_entities": [
        "Örenli İlçe Kaymakamlığı"
      ]
    },
    "source_map": {
      "applicant": "extraction.fields.person_name",
      "subject": "extraction.fields.subject",
      "request": "extraction.fields.request",
      "important_entities": "extraction.fields.institution",
      "short_summary": "deterministic_template"
    },
    "warnings": [],
    "needs_human_review": false,
    "llm": {
      "provider": "evren",
      "model": "llm-fast",
      "attempted": false,
      "status": "not_required",
      "error": null
    }
  },
  "routing": {
    "recommended_unit": null,
    "alternative_units": [
      "İlçe Nüfus Müdürlüğü",
      "Sosyal Yardımlaşma ve Dayanışma Vakfı (SYDV)"
    ],
    "ranked_units": [
      {
        "unit_id": "yazi_isleri",
        "name": "Yazı İşleri Müdürlüğü",
        "score": 50
      },
      {
        "unit_id": "nufus",
        "name": "İlçe Nüfus Müdürlüğü",
        "score": 50
      },
      {
        "unit_id": "sydv",
        "name": "Sosyal Yardımlaşma ve Dayanışma Vakfı (SYDV)",
        "score": 50
      }
    ],
    "reason": "Birden fazla birim eşit derecede olası veya yeterli kanıt yok.",
    "evidence": [],
    "routing_score": 0,
    "score_type": "rule_match",
    "score_breakdown": {
      "intent_score": 0,
      "keyword_score": 0,
      "doc_type_score": 0,
      "details": []
    },
    "registry_source": "data/institutions/kaymakamlik/kurum_profili_kaymakamlik.yaml",
    "needs_human_review": true,
    "warnings": [
      "Yönlendirme skoru düşük veya birimler arası fark çok az. Yanlış birim atamamak için manuel inceleme önerilir."
    ],
    "routing_confidence_type": "rule_margin"
  },
  "draft": {
    "draft_type": "cevap_yazisi",
    "draft_type_reason": "Başvuru sahibinin talebine (idari inceleme) doğrudan yanıt vermek amacıyla hazırlanacak resmi yazıdır.",
    "draft_generation_mode": "llm",
    "draft": {
      "sender_unit": null,
      "recipient": "Örenli İlçe Kaymakamlığı",
      "subject": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi Başvurusu Hk.",
      "body": "Örenli İlçe Kaymakamlığına,\n\nPolat Madencilik adına Pelin Sönmez tarafından Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi konusunda yapılan ve idari inceleme talep edilen başvurunuz incelenmiştir.\n\nBaşvurunuzun işleme alınmış olduğu bilgilerini rica ederim.",
      "closing": null
    },
    "rendered_text": "Örenli İlçe Kaymakamlığı\n\nKonu: Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi Başvurusu Hk.\n\nÖrenli İlçe Kaymakamlığına,\n\nPolat Madencilik adına Pelin Sönmez tarafından Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi konusunda yapılan ve idari inceleme talep edilen başvurunuz incelenmiştir.\n\nBaşvurunuzun işleme alınmış olduğu bilgilerini rica ederim.",
    "official_render": {
      "attempted": true,
      "success": true,
      "template": "cevap_yazisi.jinja2",
      "missing_fields": [
        "tc_baslik.birim_adi",
        "sayi",
        "tarih",
        "ilgi",
        "imza.ad_soyad",
        "imza.unvan"
      ],
      "warnings": [
        "Muhatap kurum hiyerarşisi bilinmiyor; canonical üst makam fallback kapanışı kullanıldı.",
        "Taslak önizlemesinde eksik alanlar açık placeholder olarak gösterildi; personel/EBYS tarafından tamamlanmalıdır."
      ],
      "source_map": {
        "tc_baslik.idare_adi": "institution_profile.kurum_adi",
        "sayi": "placeholder: outgoing EBYS metadata unavailable",
        "tarih": "placeholder: outgoing EBYS metadata unavailable",
        "konu": "extraction.fields.subject.value",
        "muhatap": "extraction.fields.recipient.value",
        "kapalis_ifadesi": "derived_from_context.muhatap_turu",
        "metin_paragraflari": "draft.body",
        "imza.ad_soyad": "placeholder: signer unavailable",
        "imza.unvan": "placeholder: signer title unavailable"
      },
      "fallback_policies": {
        "muhatap_turu": "unknown_hierarchy_as_kurum_ust"
      },
      "context": {
        "tc_baslik": {
          "idare_adi": "ÖRENLI İLÇE KAYMAKAMLIĞI",
          "birim_adi": "[BİRİM ADI]"
        },
        "sayi": "[SAYI]",
        "tarih": "[TARİH]",
        "konu": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi",
        "muhatap": {
          "tur": "kurum",
          "isim": "ÖRENLI İLÇE KAYMAKAMLIĞI"
        },
        "muhatap_turu": "kurum_ust",
        "kapalis_ifadesi": "arz ederim.",
        "ilgi": [
          {
            "tarih": "[İLGİ TARİHİ]",
            "sayi": "[İLGİ SAYISI]",
            "aciklama": "ilgi yazınız"
          }
        ],
        "metin_paragraflari": [
          "Örenli İlçe Kaymakamlığına,",
          "Polat Madencilik adına Pelin Sönmez tarafından Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi konusunda yapılan ve idari inceleme talep edilen başvurunuz incelenmiştir.",
          "Başvurunuzun işleme alınmış olduğu bilgilerini rica ederim."
        ],
        "imza": {
          "ad_soyad": "[AD SOYAD]",
          "unvan": "[UNVAN]",
          "yetki_turu": "normal"
        },
        "ekler": [],
        "dagitim": null,
        "iletisim": {
          "adres": "",
          "irtibat": ""
        },
        "sayfa_no": null,
        "uygunsuz_belge_uyarisi": null
      }
    },
    "official_rendered_text": "\n\n\n\n\nT.C.\nÖRENLI İLÇE KAYMAKAMLIĞI\n[BİRİM ADI]\n\n\n\nSayı: [SAYI]                                                                    Tarih: [TARİH]\n\n\nKonu: Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi\n\n\n\n                              ÖRENLI İLÇE KAYMAKAMLIĞI\n\n\n\n\n\n\nİlgi: [İLGİ TARİHİ] tarihli ve [İLGİ SAYISI] sayılı ilgi yazınız.\n\n\n\n\n\n\n\n\n\n\n\n\tÖrenli İlçe Kaymakamlığına,\n\tPolat Madencilik adına Pelin Sönmez tarafından Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi konusunda yapılan ve idari inceleme talep edilen başvurunuz incelenmiştir.\n\tBaşvurunuzun işleme alınmış olduğu bilgilerini rica ederim.\n\n\n\narz ederim.\n\n\n\n                                    [AD SOYAD]\n                                    [UNVAN]\n\n\n\n\nEk konulmadı.\n\n\n\n\n\n\n\n________________________________________________________________________________\n                                                                                \n",
    "process_explanation": "Sistem evrakın içeriğine göre cevap yazısı hazırlanmasını önerdi. Oluşturulan taslak nihai işlemden önce yetkili personelin onayına sunulmalıdır.",
    "applied_rules": [],
    "supporting_rules": [
      {
        "evidence": "Tekit yazıları amacı itibarıyla hiyerarşi yönünden alt veya aynı düzey idarelere yazılmalıdır.",
        "source": "K2"
      },
      {
        "evidence": "sayılı ...” ibaresi kullanılır ve ilginin sonuna nokta (.)",
        "source": "K5"
      },
      {
        "evidence": "istendiğinde, ilgi bölümü “İsimsiz ve tarihsiz başvuru/dilekçe.” biçiminde yazılır.",
        "source": "K5"
      }
    ],
    "rule_validation": {
      "proposed": 0,
      "validated": 0
    },
    "sources": [
      {
        "score": 0.5834862,
        "chunk_id": "7cf2efd7-5396-5d4d-a399-5388fdaa6530",
        "title": "Resmî Yazışmalar Kılavuzu",
        "text": "iyle bitirilmelidir. (Örneğin; Teftiş Kurulu Başkanlığı – Personel Genel Müdürlüğü\nvb.) \nMuhatap kısmında ikinci satırda parantez içinde birim veya idare ismi belirtilen yazışmalar, birinci\nsatırda yer alan muhatap idare dikkate alınarak arz veya rica ibarelerinden uygun olanı ile\nbitirilmelidir:\nMuhatapta Parantez Kullanımı\n  ÇEVRE, ŞEHİRCİLİK VE İKLİM DEĞİŞİKLİĞİ BAKANLIĞINA\n  (Toplu Konut İdaresi Başkanlığı)\n  \n  HAZİNE VE MALİYE BAKANLIĞINA\n  (Muhasebat Genel Müdürlüğü)\n  \nAçıklama\nMetin kısmında arz veya rica durumu belgeyi\nimzalayan \nkişiye \nve \ngönderilecek \nidare\nbilgisinde yer alan  “Çevre, Şehircilik ve İklim\nDeğişikliği Bakanlığına” göre belirlenir.\nMetin kısmında arz veya rica durumu belgeyi\nimzalayan \nkişiye \nve \ngönderilecek \nidare\nbilgisinde yer alan  “Hazine ve Maliye\nBakanlığına” göre belirlenir.\nResmî yazışmaların metin sonunda kullanılan “arz” ve “rica” ibarelerinin belirlenmesinde muhatap\nidare üst yöneticisinin ek göstergesinin, protokolün ve hiyerarşinin esas alınması gibi idarelerce\ngeliştirilen yanlış yöntemler ve süreçler bulunmaktadır. “Arz” ve “rica” ibarelerinin tercih edilmesinde\nmevzuatla hiyerarşi yönünden ast-üst ilişkisinin tanımlanmadığı durumlarda metin sonunun “arz\nederim” ifadesi ile bitirilmesi uygun olacaktır. Böylelikle söz konusu ifade, resmî yazı içeriğinin önüne\ngeçmeyerek iş ve işlemlerin hızlıca yürütülmesi sağlanmış olacaktır. Örneğin; Cumhurbaşkanlığına\nbağlı  kurum ve  kuruluşlar ile bakanlıklar arasında yapılacak yazışmalara ai",
        "source": "resmi_yazisma_kilavuzu",
        "rag_domain": "official_writing",
        "law_number": "resmi_yazisma_kilavuzu",
        "document_id": null,
        "madde_no": "CHUNK_30",
        "article": "CHUNK_30",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "resmi_yazisma_kilavuzu",
          "rag_domain": "official_writing",
          "madde_no": "CHUNK_30",
          "source": "resmi_yazisma_kilavuzu",
          "title": "Resmî Yazışmalar Kılavuzu",
          "trusted_source": true
        }
      },
      {
        "score": 0.5753081,
        "chunk_id": "f0244dd0-7f6e-51e7-ba71-fdb5a6be6092",
        "title": "Resmî Yazışmalar Kılavuzu",
        "text": "anımlayıcı bilgilerle birlikte\nbelgenin muhatabı olunmadığı bilgisi, resmî yazıyla gönderen idareye iletilmelidir.\nİdareye muhatabı olmadığı hâlde fiziksel ortamda belge gelmesi durumunda:\nAsıl muhatabı anlaşılamıyorsa belge gönderene iade edilmelidir.\nAsıl muhatabın açıkça belli olması durumunda, belgenin bir sureti alınarak aslı muhatabına\ngönderilmeli ve belgeyi gönderene de bilgi verilmelidir.\n\n95\n30. TEKİT YAZISI\nYönetmelik 34. Madde\nBelgeye süresi içinde cevap verilmemesi durumunda muhataba tekit yazısı yazılabilmektedir.\nTekit yazıları amacı itibarıyla hiyerarşi yönünden alt veya aynı düzey idarelere yazılmalıdır.\nKurumlar hiyerarşi yönünden üst seviyedeki kurumlara tekit yazısı yazmamalıdır.\nTekit yazısında daha önce gönderilen belge ilgi olarak tutulmalıdır.\nTekit Yazısı Örneği\nTekit \nyazısında \ndaha \nönce\ngönderilen yazının ilgi tutulması\nzorunludur.\n\n96\n31. UYGUN YAZILMAYAN BELGELER\nYönetmelik 35. Madde\nResmî yazışmalarda uygulama birliğinin sağlanması amacıyla idareler tarafından hazırlanan veya\nteslim alınan belgeler Yönetmelik’e uygunluk açısından incelenmelidir. Herhangi bir madde hükmüne\naykırı hazırlanan bir belge teslim alındığında muhatap cevabî yazıda veya şifahen uyarılmalı,\nYönetmelik’e aykırılığın daha sonra gerçekleştirilen yazışmalarda da devam etmesi durumunda ise\naşağıda örneği verilen yazıyla muhatap uyarılmalıdır: \nMUHATAP \ngg.aa.yyyy tarihli ve …-..….-…..-….. sayılı yazınız Resmî Yazışmalarda Uygulanacak Usul ve\nEsaslar Hakkında Yönetmelik’in  ……",
        "source": "resmi_yazisma_kilavuzu",
        "rag_domain": "official_writing",
        "law_number": "resmi_yazisma_kilavuzu",
        "document_id": null,
        "madde_no": "CHUNK_83",
        "article": "CHUNK_83",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "resmi_yazisma_kilavuzu",
          "rag_domain": "official_writing",
          "madde_no": "CHUNK_83",
          "source": "resmi_yazisma_kilavuzu",
          "title": "Resmî Yazışmalar Kılavuzu",
          "trusted_source": true
        }
      },
      {
        "score": 0.57397354,
        "chunk_id": "3a37a213-8c8c-51ee-bf18-51a3b970ba65",
        "title": "Resmî Yazışmalar Kılavuzu",
        "text": "len tarih bilgisine ilgide muhakkak yer verilmelidir.\nYanlış Kullanım\nBila tarihli ve E-84801842-902.02-1042582 sayılı\nyazınız.\nDoğru Kullanım\n01.09.2019 \ntarihli \nve \nE-84801842-902.02-\n1042582 sayılı yazınız.\n\nYanlış Kullanım\n01.09.2019 tarihli ve 1042582 sayılı yazımız.\nDoğru Kullanım\n01.09.2019 \ntarihli \nve \nE-84801842-902.02-\n1042582 sayılı yazımız.\n12.3. İlgi Tutulan Belge Sayısının Yazımı \nİlgi olarak eklenen belgenin sadece kayıt numarası yazılmamalı, belgenin hazırlanma süreci ve ait\nolduğu idare/birim bilgisine de erişilebilmesi amacıyla 4 bölümden oluşan sayı, bütünüyle\nyazılmalıdır.\n28\n\n29\nİlgi tutulan belge bilgilerinin\n(tarih, sayı ve geldiği idare)\nyazılması gerekmektedir. \nMetin kısmında ilk paragrafta ilgi\ntutulan belgenin içeriği hakkında\nbilgi \nverilerek \nilgi \nile \nbelge\narasında bağ kurulmalıdır.\nİlgide \nyer \nalan \nbelge \nmuhatap\nkurumda bulunmayan bir belge ise ek\nolarak gönderilmesi uygun olacaktır.\nİlgi \ntutulan \nbelge \nkurumların\nrahatlıkla Resmî Gazete üzerinden\nulaşabileceği kanun, yönetmelik vb.\nise \nayrıca \ngönderilmesine \ngerek\nyoktur. \n\n13. METİN\nYönetmelik 16. Madde\nResmî yazılarda esas unsuru teşkil eden ve muhatabın bilgilendirildiği kısım metindir. Metin,\naşağıdaki hususlar dikkate alınarak hazırlanmalıdır:\nAçık, anlaşılabilir, kısa ve olabildiğince öz anlatım benimsenmeli,\nHerkesçe bilinen Türkçe kelimeler tercih edilmeli,\nTürkçe dil bilgisi ve yazım kurallarına uygunluk sağlanmalı (Türk Dil Kurumu Sözlüğü ve Yazım\nKılavuzu dikkate alınmalı",
        "source": "resmi_yazisma_kilavuzu",
        "rag_domain": "official_writing",
        "law_number": "resmi_yazisma_kilavuzu",
        "document_id": null,
        "madde_no": "CHUNK_28",
        "article": "CHUNK_28",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "resmi_yazisma_kilavuzu",
          "rag_domain": "official_writing",
          "madde_no": "CHUNK_28",
          "source": "resmi_yazisma_kilavuzu",
          "title": "Resmî Yazışmalar Kılavuzu",
          "trusted_source": true
        }
      },
      {
        "score": 0.57000995,
        "chunk_id": "e4a52b71-d415-53c5-81b6-2642a25a52ca",
        "title": "Resmî Yazışmalar Kılavuzu",
        "text": "re ismi yer almalıdır. Ayrıca farklı idarelerde\naynı birim adı olabileceğinden karışıklığa yol\naçmaması adına idare ismi kullanılmalıdır.\n26\n\n12. İLGİ\n27\nYönetmelik 15. Madde\nİlgi, iki yana yaslı olarak yazılan ve birden fazla olduğunda belgelerin tarih sırasına göre kronolojik\ndüzenlendiği alandır. İlgide aşağıdaki bilgilerin yer alması gerekmektedir.\n12.1.  İlgi Tutulan Belgenin Sahibi İdarenin Yazımı\nİlgi Kullanımı\nTicaret Bakanlığının (Personel Genel Müdürlüğü)\n01.09.2019 \ntarihli \nve \nE-35799330-902.02-\n1042579 sayılı yazısı.\nAçıklama\nİdare \ndışına \ngönderilen \nbelgelerde, \nsadece\n“Personel Genel Müdürlüğünün … tarihli ve ...\nsayılı yazısı” yazıldığı takdirde, belge sahibinin\nhangi idare olduğu anlaşılamayacağından idare\nisminin \n(Ticaret \nBakanlığı) \nyazılması\ngerekmektedir.\nYanlış Kullanım\nStrateji Geliştirme Daire Başkanlığının 01.09.2019\ntarihli E-84801842-902.02-1042580 sayılı yazısı.\nDoğru Kullanım\nAfyon Kocatepe Üniversitesi Rektörlüğünün\n(Strateji Geliştirme Daire Başkanlığı) 01.09.2019\ntarihli ve E-84801842-902.02-1042580 sayılı\nyazısı.\nİlgi tutulan belgelerden yazı içinde bahsedilmelidir. İlgi tutulan belgenin muhatapta olmaması\ndurumunda, belge muhataba ek olarak iletilmelidir.\nİlgi tutulan belge, Resmî Gazete’de yayımlanan bir mevzuat ise ayrıca ek olarak eklenmemelidir. \n12.2. İlgi Tutulan Belge Tarihinin Yazımı\nİlgi kısmında vatandaş başvuruları haricinde “bila tarihli” veya “tarihsiz” ifadesi kullanılmamalıdır.\nBelgenin görüntüsünden ve üstverisinden erişi",
        "source": "resmi_yazisma_kilavuzu",
        "rag_domain": "official_writing",
        "law_number": "resmi_yazisma_kilavuzu",
        "document_id": null,
        "madde_no": "CHUNK_27",
        "article": "CHUNK_27",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "resmi_yazisma_kilavuzu",
          "rag_domain": "official_writing",
          "madde_no": "CHUNK_27",
          "source": "resmi_yazisma_kilavuzu",
          "title": "Resmî Yazışmalar Kılavuzu",
          "trusted_source": true
        }
      },
      {
        "score": 0.5577692,
        "chunk_id": "fe42ad7a-7fed-51b2-a9d9-2edc45d3088b",
        "title": "Resmî Yazışmalarda Uygulanacak Usul ve Esaslar Hakkında Yönetmelik",
        "text": "MADDE 15- (1) İlgi, belgenin bağlantılı olduğu diğer belge veya belgelerin\nbelirtildiği bölümdür.\n\n(2) “İlgi:” yan başlığı, muhatap bölümünün son satırından itibaren iki satır boşluk\nbırakılarak ve yazı alanının solundan başlanarak yazılır (Örnek 7).\n\n(3) “Sayı”, “Konu” ve “İlgi” yan başlıklarından sonra kullanılan iki nokta\naynı hizada yazılır (Örnek 7).\n\n(4) İlgide yer alan bilgiler bir satırı geçerse, devamı “İlgi:” yan başlığının ve\nsıralamayı gösteren harflerin altı boş bırakılarak alt satıra yazılır (Örnek 7).\n\n(5) İlginin birden fazla olması durumunda, belgeler önceki tarihli olandan\nbaşlanarak tarih sırasına göre sıralanır. Sıralamada, Türk alfabesinde yer alan bütün küçük\nharfler, kendilerinden sonra kapama parantez işareti “)” konularak kullanılır (Örnek 7).\n\n(6) İlgide, ilgi tutulan belgeyi gönderen idarenin adı ile belgenin tarihi ve sayısı\nbelirtilir. Ancak ilgi tutulan belgenin, muhatap idarenin daha önce gönderdiği bir belge\nveya muhatap idareye daha önce gönderilen bir belge olması durumunda idare adı\nbelirtilmez (Örnek 7).\n\n(7) İlgide, “... tarihli ve ... sayılı ...” ibaresi kullanılır ve ilginin sonuna nokta (.)\nişareti konulur (Örnek 7).\n\n(8) İlgide belirtilen belge, muhatapta bulunmadığı durumlarda söz konusu belge, ek\nolarak muhatabına iletilebilir (Örnek 7).\n\n(9) İlgide belirtilen belge, gerçek kişiden geliyorsa ilgi bölümü “...ın ... tarihli\nbaşvurusu/dilekçesi.” biçiminde yazılır (Örnek 9). Ancak belgenin muhatabı, ilgi tutulan\nbaşvurunun veya dilekçenin sahibi ise ilgi bölümünde gerçek kişinin isim bilgisine yer\nverilmez.\n\n(10) Gerçek kişi ve tarih bilgisi bulunmayan başvuru/dilekçe ilgi tutulmak\nistendiğinde, ilgi bölümü “İsimsiz ve tarihsiz başvuru/dilekçe.” biçiminde yazılır. Söz\nkonusu başvurunun/dilekçenin işleme alınıp alınmayacağı ilgili mevzuat hükümlerine göre\ndeğerlendirilir.\n\n«>\n\nişareti\n\n«\n\nMetin",
        "source": "resmi_yazisma_yonetmeligi",
        "rag_domain": "official_writing",
        "law_number": "resmi_yazisma_yonetmeligi",
        "document_id": null,
        "madde_no": "15",
        "article": "15",
        "trusted_source": true,
        "metadata": {
          "rag_eligible": true,
          "law_number": "resmi_yazisma_yonetmeligi",
          "rag_domain": "official_writing",
          "madde_no": "15",
          "source": "resmi_yazisma_yonetmeligi",
          "title": "Resmî Yazışmalarda Uygulanacak Usul ve Esaslar Hakkında Yönetmelik",
          "trusted_source": true
        }
      }
    ],
    "retrieval_score": 0.5835,
    "llm": {
      "provider": "evren",
      "model": "llm-fast"
    },
    "verified_facts_used": [
      "İşlem Türü: basvuru"
    ],
    "requires_human_approval": true,
    "needs_additional_context": false,
    "warning": null
  }
}
```

**State'e yazılan tam çıktı:**

```json
{
  "status": "warning",
  "checks": {
    "document_classification": {
      "status": "pass",
      "message": "Evrak sınıflandırması mevcut."
    },
    "extraction": {
      "status": "warning",
      "message": "Çıkarım sonuçlarında eksik kanıtlı alanlar var veya onay gerekiyor."
    },
    "missing_fields": {
      "status": "warning",
      "message": "Eksik alan analizi personel incelemesi gerektiriyor."
    },
    "legal_evidence": {
      "status": "warning",
      "message": "Kaynak bulundu ancak doğrulanmış hukuki kanıt çıkarılamadı."
    },
    "routing": {
      "status": "warning",
      "message": "Birim yönlendirmesi belirsiz, manuel inceleme gerekiyor."
    },
    "summary": {
      "status": "pass",
      "message": "Özet tutarlı."
    },
    "draft": {
      "status": "warning",
      "message": "Taslak metin personel onayı gerektiriyor."
    },
    "official_format": {
      "status": "warning",
      "message": "Resmî taslak önizlemesi oluşturuldu; personel/EBYS tarafından doldurulacak alanlar: tc_baslik.birim_adi, sayi, tarih, ilgi, imza.ad_soyad, imza.unvan."
    },
    "official_writing_format": {
      "status": "warning",
      "message": "Resmî yazı biçim uyarıları: Sayı alanı taslak önizlemesinde placeholder olarak gösterildi; personel/EBYS tarafından doldurulmalıdır.; Tarih alanı taslak önizlemesinde placeholder olarak gösterildi; personel/EBYS tarafından doldurulmalıdır.; İlgi alanı taslak önizlemesinde placeholder olarak gösterildi; personel/EBYS tarafından doldurulmalıdır."
    },
    "human_review": {
      "status": "warning",
      "message": "Kritik işlemler veya belirsizlikler nedeniyle personel onayı gerekiyor."
    }
  },
  "issues": [],
  "warnings": [
    "Çıkarım sonuçlarında eksik kanıtlı alanlar var veya onay gerekiyor.",
    "Eksik alan analizi personel incelemesi gerektiriyor.",
    "Kaynak bulundu ancak doğrulanmış hukuki kanıt çıkarılamadı.",
    "Birim yönlendirmesi belirsiz, manuel inceleme gerekiyor.",
    "Taslak metin personel onayı gerektiriyor.",
    "Resmî taslak önizlemesi oluşturuldu; personel/EBYS tarafından doldurulacak alanlar: tc_baslik.birim_adi, sayi, tarih, ilgi, imza.ad_soyad, imza.unvan.",
    "Resmî yazı biçim uyarıları: Sayı alanı taslak önizlemesinde placeholder olarak gösterildi; personel/EBYS tarafından doldurulmalıdır.; Tarih alanı taslak önizlemesinde placeholder olarak gösterildi; personel/EBYS tarafından doldurulmalıdır.; İlgi alanı taslak önizlemesinde placeholder olarak gösterildi; personel/EBYS tarafından doldurulmalıdır.",
    "Kritik işlemler veya belirsizlikler nedeniyle personel onayı gerekiyor."
  ],
  "requires_human_review": true
}
```
### human_review_agent

**Tam tüketilen giriş:**

```json
{}
```

**State'e yazılan tam çıktı:**

```json
{
  "required": true,
  "status": "pending_review"
}
```


## LLM canlı promptları ve ham yanıtları

### LLM çağrısı 1: shared_fast — evren / llm-fast

Sıcaklık: `0.0`; max_tokens: `300`; JSON modu: `True`.

**Tam sistem promptu**

```text

Sen kamu kurumlarına gelen evrakları sınıflandıran
bir evrak analiz sistemisin.

SADECE aşağıdaki document_type değerlerini kullan:

dilekce
resmi_yazi
form
tutanak
rapor
karar
tebligat
eposta
diger

SADECE aşağıdaki process_intent değerlerini kullan:

bilgi_talebi
belge_talebi
basvuru
sikayet
itiraz
izin_talebi
bildirim
cevap
iletim
diger

KESİN KURALLAR:

1. Sadece verilen evrak metnini kullan.

2. Evrakta olmayan bilgi veya amaç uydurma.

3. Emin değilsen diger seç.

4. evidence içindeki text alanı evrakta gerçekten
   geçen ifade olmalıdır.

5. subject:
   Evrakın ana konusunu gösteren kaynak ifadesi.

6. request:
   Gönderenin temel talebini gösteren kaynak ifadesi.

7. Talep yoksa request evidence oluşturma.

8. JSON dışında hiçbir şey yazma.

SADECE:

{
    "document_type": "dilekce",
    "process_intent": "bilgi_talebi",
    "evidence": [
        {
            "field": "subject",
            "text": "kaynak metindeki ifade"
        },
        {
            "field": "request",
            "text": "kaynak metindeki ifade"
        }
    ]
}

```

**Tam kullanıcı promptu**

```text

EVRAK:

ÖRENLİ İLÇE KAYMAKAMLIĞINA

BAŞVURAN: Polat Madencilik adına Pelin Sönmez

KONU: Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi

AÇIKLAMALAR:
1. Kurum araçları akaryakıt alımı ihalesinin idari şartnamesi ile sözleşme tasarısında ödeme vadelerine ilişkin birbiriyle çelişkili maddeler bulunmaktadır, idari inceleme talep ediyoruz.
2. 4734 sayılı Kamu İhale Kanunu uyarınca gerekli yasal incelemenin yapılmasını talep ediyoruz.
3. Gereğinin ivedilikle yapılmasını arz ederim.

İmza: Polat Madencilik adına Pelin Sönmez

Evrakı sınıflandır.

```

**Ham LLM yanıtı**

```text
{
    "document_type": "dilekce",
    "process_intent": "basvuru",
    "evidence": [
        {
            "field": "subject",
            "text": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi"
        },
        {
            "field": "request",
            "text": "idari inceleme talep ediyoruz"
        }
    ]
}
```
### LLM çağrısı 2: shared_fast — evren / llm-fast

Sıcaklık: `0.0`; max_tokens: `500`; JSON modu: `True`.

**Tam sistem promptu**

```text

Sen kamu evrakı bilgi çıkarım sistemisin.
Görev: Metindeki ilgili alanları JSON olarak çıkarmak.

KURALLAR:
1. SADECE metinde yer alan bilgileri çıkar.
2. value normalize edilebilir, ancak evidence metindeki EXACT (birebir aynı) ifade olmak zorundadır.
3. Bulamadığın alanlar için json key üretme veya boş string/null bırak.
4. SADECE JSON formatında çıktı ver.

ÇIKARILACAK ALANLAR (SADECE BUNLARI ÇIKAR):
- address: Adres
- institution: Kamu kurumu / T.C. X Kurumu
- sender_unit: Gönderen birim
- recipient: Hitap edilen muhatap / Alıcı birim (Örn: Bilgi Edinme Birimine)
- other_entities: (Tarih, mekan vb. ek varlıklar liste halinde. type: organization|date|location)

FORMAT ÖRNEĞİ (SADECE İSTENEN ALANLAR İÇİN):
{
    "hedef_alan_1": {"value": "Örnek Değer", "evidence": "Örnek Değer"}
}

```

**Tam kullanıcı promptu**

```text
EVRAK METNİ:
ÖRENLİ İLÇE KAYMAKAMLIĞINA

BAŞVURAN: Polat Madencilik adına Pelin Sönmez

KONU: Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi

AÇIKLAMALAR:
1. Kurum araçları akaryakıt alımı ihalesinin idari şartnamesi ile sözleşme tasarısında ödeme vadelerine ilişkin birbiriyle çelişkili maddeler bulunmaktadır, idari inceleme talep ediyoruz.
2. 4734 sayılı Kamu İhale Kanunu uyarınca gerekli yasal incelemenin yapılmasını talep ediyoruz.
3. Gereğinin ivedilikle yapılmasını arz ederim.

İmza: Polat Madencilik adına Pelin Sönmez

Lütfen yukarıdaki evrak için bilgileri çıkar.
```

**Ham LLM yanıtı**

```text
{
    "address": {
        "value": "Örenli İlçe Kaymakamlığı",
        "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA"
    },
    "institution": {
        "value": "Örenli İlçe Kaymakamlığı",
        "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA"
    },
    "sender_unit": {
        "value": "Polat Madencilik",
        "evidence": "Polat Madencilik"
    },
    "recipient": {
        "value": "Örenli İlçe Kaymakamlığı",
        "evidence": "ÖRENLİ İLÇE KAYMAKAMLIĞINA"
    },
    "other_entities": [
        {
            "type": "organization",
            "value": "Polat Madencilik",
            "evidence": "Polat Madencilik"
        },
        {
            "type": "organization",
            "value": "Polat Madencilik",
            "evidence": "Polat Madencilik"
        }
    ]
}
```
### LLM çağrısı 3: legal_large — evren / llm-large

Sıcaklık: `0.0`; max_tokens: `450`; JSON modu: `True`.

**Tam sistem promptu**

```text

Sen kaynak-temelli bir Türkçe mevzuat bilgi çıkarım sistemisin.

KURALLAR:
1. Yalnızca verilen kaynakları kullan.
2. Kaynaklarda bulunmayan hukuki yorum, bilgi veya sonuç üretme.
3. Evidence kısa olmalı ve ilgili kaynak metninde birebir doğrulanabilmelidir.
4. Kaynaklar soruyu doğrudan cevaplamıyorsa tahmin etme ve {"items":[]} döndür.
5. Yalnızca şu JSON şemasını döndür; JSON dışında açıklama yazma:
   {"items":[{"evidence":"kaynakta geçen kısa ifade","source":"K1"}]}

ÖRNEK 1 — kaynak cevaplıyor:
Soru: Başvuru kaç gün içinde cevaplanır?
K1 Metin: Başvurunun sonucu en geç otuz gün içinde bildirilir.
Çıktı: {"items":[{"evidence":"Başvurunun sonucu en geç otuz gün içinde bildirilir.","source":"K1"}]}

ÖRNEK 2 — kaynak cevaplamıyor:
Soru: Başvuru ücreti ne kadardır?
K1 Metin: Başvurunun sonucu yazılı olarak bildirilir.
Çıktı: {"items":[]}

```

**Tam kullanıcı promptu**

```text

SORU:
basvuru Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi idari inceleme talep ediyoruz

MEVZUAT KAYNAKLARI:
[K1]
Kaynak Adı: Kamu İhale Kanunu (4734)
Kanun/Yönetmelik No: 4734
Madde: 56
Metin:
Madde 56- (Değişik: 22/11/2008-5812/23 md.) 
İdareye şikayet başvurusunda bulunan veya idarece alınan kararı uygun bulmayan aday, 
istekli veya istekli olabilecekler tarafından 55 inci maddenin dördüncü fıkrasında belirtilen 
hallerde ve sürede, sözleşme imzalanmadan önce itirazen şikayet başvurusunda bulunulabilir. 
İhalenin iptaline ilişkin işlem ve kararlardan, sadece şikayet ve itirazen şikayet üzerine alınanlar 
itirazen şikayete konu edilebilir ve bu kararlara karşı beş gün içinde doğrudan Kuruma başvuruda 
bulunulabilir. 
Kurum itirazen şikayet başvurularını başvuru sahibinin iddiaları ile idarenin şikayet 
üzerine aldığı kararda belirlenen hususlar ve itiraz edilen işlemler bakımından eşit muamele 
ilkesinin ihlal edilip edilmediği açılarından inceler. İdare tarafından şikayet veya itirazen şikayet 
üzerine alınan ihalenin iptal edilmesi işlemine karşı yapılacak itirazen şikayet başvuruları ise 
idarenin iptal gerekçeleriyle sınırlı incelenir. 
Kanunda belirtilen sürelere ve usule uyulmadan sözleşme imzalanmış olması veya itirazen 
şikayet başvurusundan feragat edilmesi itirazen şikayet başvurusunun incelenmesine ve 54 üncü 
maddede sayılan kararlardan birinin alınmasına engel teşkil etmez. 
 
60 20/11/2008 tarihli ve 5812 sayılı Kanunun 23 üncü maddesiyle bu madde başlığı “Kamu İhale Kurulu 
tarafından inceleme” iken, 5/1/2009 tarihinden geçerli olmak üzere metne işlendiği şekilde 
değiştirilmiştir. 

Kurul tarafından gerekli görülen hallerde tarafların ve ilgililerin dinlenmesine karar 
verilir. Bu durumda, Kurul tarafından tespit edilen tarihte taraflar ve ilgililer dinlenir. 
Kurum, itirazen şikayete ilişkin nihai kararını, incelenen ihaleye ilişkin gerekli bilgi ve 
belgeler ile ihale işlem dosyasının kayıtlara alındığı tarihi izleyen yirmi gün içinde vermek 
zorundadır. Bu süre 21 inci maddenin (b) ve (c) bentlerine göre yapılan ihaleler ile şikayet ve 
itirazen şikayet üzerine alınan ihalenin iptal edilmesi işlemine karşı yapılacak itirazen şikayet 
b

---

[K2]
Kaynak Adı: Kamu İhale Kanunu (4734)
Kanun/Yönetmelik No: 4734
Madde: 54
Metin:
Madde 54- (Değişik: 20/11/2008-5812/21 md.)  
İhale sürecindeki hukuka aykırı işlem veya eylemler nedeniyle bir hak kaybına veya 
zarara uğradığını veya zarara uğramasının muhtemel olduğunu iddia eden aday veya istekli ile 
istekli olabilecekler, bu Kanunda belirtilen şekil ve usul kurallarına uygun olmak şartıyla şikayet 
ve itirazen şikayet başvurusunda bulunabilirler. 
Şikayet ve itirazen şikayet başvuruları, dava açılmadan önce tüketilmesi zorunlu idari 
başvuru yollarıdır. 
Şikayet başvuruları idareye, itirazen şikayet başvuruları Kuruma hitaben yazılmış imzalı 
dilekçelerle yapılır.  
Dilekçelerde aşağıdaki hususlara yer verilir: 
a) Başvuru sahibinin, varsa vekil ya da temsilcisinin adı, soyadı veya unvanı ve adresi. 
b) İhaleyi yapan idarenin ve ihalenin adı veya ihale kayıt numarası. 
c) Başvuruya konu olan durumun farkına varıldığı veya bildirildiği tarih. 
d) Başvurunun konusu, sebepleri ve dayandığı deliller. 
e) İtirazen şikayet başvurularında idareye yapılan şikayetin ve varsa şikayete ilişkin idare 
kararının bildirim tarihi. 
(Değişik beşinci fıkra:28/1/2021-7263/10 md.) Şikâyet ve itirazen şikâyet başvuru 
dilekçelerinde yer alması gereken diğer bilgiler ile bu dilekçelere eklenmesi gereken belgelere, 
bunların sunuluş şekli ile bu başvuruların elektronik ortamda yapılmasına ilişkin usul ve esasları 
belirlemeye Kurum yetkilidir.  
İtirazen şikayette bulunanlardan 53 üncü maddenin (j) bendinin (2) nolu alt bendinde 
belirtilen bedelin dört katı tutarına kadar başvuru teminatı alınmasına Cumhurbaşkanınca karar 
verilebilir. Başvuru teminatları Kurum hesaplarına yatırılır. Bu teminatlar Kurum gelirleri ile 
ilişkilendirilmeksizin ayrı hesaplarda tutulur.58 
(Mülga yedinci fıkra:28/1/2021-7263/10 md.)  
Aynı kişi tarafından birden fazla ihaleye, birden fazla kişi tarafından ise aynı ihaleye tek 
dilekçe ile başvuruda bulunulamaz. 
(Ek: 6/2/2014-6518/50 md.) Başvuruların ihaleyi yapan idare veya Kurum dışındaki idari 
 
56 20/11/2008 tarihli ve 5812 say

---

[K3]
Kaynak Adı: Kamu İhale Kanunu (4734)
Kanun/Yönetmelik No: 4734
Madde: 37
Metin:
Madde 37- İhale komisyonunun talebi üzerine idare tekliflerin incelenmesi, 
karşılaştırılması ve değerlendirilmesinde yararlanmak üzere net olmayan hususlarla ilgili 
isteklilerden yazılı olarak tekliflerini açıklamalarını isteyebilir. Ancak bu açıklama, hiçbir şekilde 
teklif fiyatında değişiklik yapılması veya ihale dokümanında yer alan şartlara uygun olmayan 
tekliflerin uygun hale getirilmesi amacıyla istenilmez ve yapılmaz.  
(Değişik ikinci fıkra: 20/11/2008-5812/11 md.) Tekliflerin değerlendirilmesinde, 
öncelikle belgeleri eksik olduğu veya teklif mektubu ile geçici teminatı usulüne uygun olmadığı 
36 ncı maddeye göre ilk oturumda tespit edilen isteklilerin tekliflerinin değerlendirme dışı 
bırakılmasına karar verilir. Ancak, teklifin esasını değiştirecek nitelikte olmaması kaydıyla, 
belgelerde bilgi eksikliği bulunması halinde idarece belirlenen sürede isteklilerden bu eksik 
bilgilerin tamamlanması yazılı olarak istenir. Belirlenen sürede bilgileri tamamlamayan istekliler 
değerlendirme dışı bırakılır ve geçici teminatları gelir kaydedilir. Bu ilk değerlendirme ve 
işlemler sonucunda belgeleri eksiksiz ve teklif mektubu ile geçici teminatı usulüne uygun olan 
isteklilerin tekliflerinin ayrıntılı değerlendirilmesine geçilir. Bu aşamada, isteklilerin ihale konusu 
işi yapabilme kapasitelerini belirleyen yeterlik kriterlerine ve tekliflerin ihale dokümanında 
belirtilen şartlara uygun olup olmadığı ile birim fiyat teklif cetvellerinde aritmetik hata bulunup 
bulunmadığı incelenir. Uygun olmadığı belirlenen isteklilerin teklifleri ile birim fiyat teklif 
cetvellerinde aritmetik hata bulunan teklifler değerlendirme dışı bırakılır. 
(Mülga son fıkra: 20/11/2008-5812/11 md.) 
 
36 20/11/2008 tarihli ve 5812 sayılı Kanunun 10 uncu maddesiyle; bu fıkrada yer alan “teklif fiyatları 
açıklanır” ibaresi “teklif fiyatları ve yaklaşık maliyet tutarı açıklanır” şeklinde değiştirilmiştir. 

 
Aşırı düşük teklifler

Soruyu doğrudan cevaplayan kısa kaynak ifadelerini JSON şemasında çıkar.

```

**Ham LLM yanıtı**

```text
{"items":[]}
```
### LLM çağrısı 4: shared_fast — evren / llm-fast

Sıcaklık: `0.0`; max_tokens: `120`; JSON modu: `True`.

**Tam sistem promptu**

```text

Sen kamu evrak süreçlerinde hangi resmî yazı türünün
hazırlanması gerektiğini belirleyen bir karar destek
bileşenisin.

SADECE aşağıdaki değerlerden birini seç:

ust_yazi
cevap_yazisi
bilgilendirme_metni
diger

ust_yazi:
Bir evrakın veya ekin başka bir kurum ya da birime
resmî olarak iletilmesi için hazırlanır.

cevap_yazisi:
Bir başvuru, talep veya resmî yazıya doğrudan cevap
vermek için hazırlanır.

bilgilendirme_metni:
Bir kişi veya ilgili tarafa süreç ya da durum hakkında
genel bilgi vermek için hazırlanır.

diger:
Yukarıdaki türlere açık şekilde girmeyen durumlarda
kullanılır.

Yeni olay, kurum veya mevzuat uydurma.
JSON dışında hiçbir şey döndürme.

{
    "draft_type": "cevap_yazisi",
    "reason": "kısa gerekçe"
}

```

**Tam kullanıcı promptu**

```text

EVRAK ÖZETİ:

Polat Madencilik adına Pelin Sönmez tarafından Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi konusunda başvuru yapılmıştır. Başvuruda idari inceleme talep ediyoruz talep edilmektedir.

ÖNERİLEN İŞLEM:

basvuru

En uygun resmî yazı türünü seç.

```

**Ham LLM yanıtı**

```text
{
    "draft_type": "cevap_yazisi",
    "reason": "Başvuru sahibinin talebine (idari inceleme) doğrudan yanıt vermek amacıyla hazırlanacak resmi yazıdır."
}
```
### LLM çağrısı 5: shared_fast — evren / llm-fast

Sıcaklık: `0.0`; max_tokens: `350`; JSON modu: `True`.

**Tam sistem promptu**

```text

Sen Türkiye'deki kamu kurumları için resmî yazı
taslağı hazırlayan bir asistansın.

KESİN KURALLAR:

1. subject ve body alanları boş olamaz.

2. Öncelikli gerçek kaynağın DOĞRULANMIŞ İŞLEM
   BİLGİLERİ bölümüdür.

3. DOĞRULANMIŞ İŞLEM BİLGİLERİ verilmişse cevap
   metnindeki işlem durumu veya sonuç yalnızca bu
   bilgilerden oluşturulmalıdır.

4. Verilmeyen kurum, kişi, tarih, belge sayısı,
   dosya numarası, süre, kanun, yönetmelik veya
   hukuki sonuç uydurma.

5. Evrakın anlamını değiştirme.

6. Resmî, kısa ve profesyonel Türkçe kullan.

7. Cevap yazısında yalnızca verilen işlem durumunu
   veya sonucu bildir.

8. Eksik bilgi talebi ise yalnızca verilen eksik
   alanların tamamlanmasını iste.

9. Kılavuzda bulunan örnek olayları taslağa taşıma.

10. JSON dışında hiçbir şey döndürme.

SADECE ŞU JSON FORMATINI DÖNDÜR:

{
    "subject": "kısa ve açık konu",
    "body": "resmî yazının ana metni"
}

```

**Tam kullanıcı promptu**

```text

YAZI TÜRÜ:
cevap_yazisi

EVRAK ÖZETİ:
Polat Madencilik adına Pelin Sönmez tarafından Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi konusunda başvuru yapılmıştır. Başvuruda idari inceleme talep ediyoruz talep edilmektedir.

ÖNERİLEN İŞLEM:
basvuru

EKSİK ALANLAR:
Yok

DOĞRULANMIŞ İŞLEM BİLGİLERİ:
- İşlem Türü: basvuru

MUHATAP:
Örenli İlçe Kaymakamlığı

GÖNDEREN:
BELİRTİLMEDİ

KILAVUZ KAYNAKLARI:
[K1]
Kaynak: Resmî Yazışma Kılavuzu

iyle bitirilmelidir. (Örneğin; Teftiş Kurulu Başkanlığı – Personel Genel Müdürlüğü
vb.) 
Muhatap kısmında ikinci satırda parantez içinde birim veya idare ismi belirtilen yazışmalar, birinci
satırda yer alan muhatap idare dikkate alınarak arz veya rica ibarelerinden uygun olanı ile
bitirilmelidir:
Muhatapta Parantez Kullanımı
  ÇEVRE, ŞEHİRCİLİK VE İKLİM DEĞİŞİKLİĞİ BAKANLIĞINA
  (Toplu Konut İdaresi Başkanlığı)
  
  HAZİNE VE MALİYE BAKANLIĞINA
  (Muhasebat Genel Müdürlüğü)
  
Açıklama
Metin kısmında arz veya rica durumu belgeyi
imzalayan 
kişiye 
ve 
gönderilecek 
idare
bilgisinde yer alan  “Çevre, Şehircilik ve İklim
Değişikliği Bakanlığına” göre belirlenir.
Metin kısmında arz veya rica durumu belgeyi
imzalayan 
kişiye 
ve 
gönderilecek 
idare
bilgisinde yer alan  “Hazine ve Maliye
Bakanlığına” göre belirlenir.
Resmî yazışmaların metin sonunda kullanılan “arz” ve “rica” ibarelerinin belirlenmesinde muhatap
idare üst yöneticisinin ek göstergesinin, protokolün ve hiyerarşinin esas alınması gibi idarelerce
geliştirilen yanlış yöntemler ve süreçler bulunmaktadır. “Arz” ve “rica” ibarelerinin tercih edilmesinde
mevzuatla hiyerarşi yönünden ast-üst ilişkisinin tanımlanmadığı durumlarda metin sonunun “arz
ederim” ifadesi ile bitirilmesi uygun olacaktır. Böylelikle söz konusu ifade, resmî yazı içeriğinin önüne
geçmeyerek iş ve işlemlerin hızlıca yürütülmesi sağlanmış olacaktır. Örneğin; Cumhurbaşkanlığına
bağlı  kurum ve  kuruluşlar ile bakanlıklar arasında yapılacak yazışmalara ai

---

[K2]
Kaynak: Resmî Yazışma Kılavuzu

anımlayıcı bilgilerle birlikte
belgenin muhatabı olunmadığı bilgisi, resmî yazıyla gönderen idareye iletilmelidir.
İdareye muhatabı olmadığı hâlde fiziksel ortamda belge gelmesi durumunda:
Asıl muhatabı anlaşılamıyorsa belge gönderene iade edilmelidir.
Asıl muhatabın açıkça belli olması durumunda, belgenin bir sureti alınarak aslı muhatabına
gönderilmeli ve belgeyi gönderene de bilgi verilmelidir.

95
30. TEKİT YAZISI
Yönetmelik 34. Madde
Belgeye süresi içinde cevap verilmemesi durumunda muhataba tekit yazısı yazılabilmektedir.
Tekit yazıları amacı itibarıyla hiyerarşi yönünden alt veya aynı düzey idarelere yazılmalıdır.
Kurumlar hiyerarşi yönünden üst seviyedeki kurumlara tekit yazısı yazmamalıdır.
Tekit yazısında daha önce gönderilen belge ilgi olarak tutulmalıdır.
Tekit Yazısı Örneği
Tekit 
yazısında 
daha 
önce
gönderilen yazının ilgi tutulması
zorunludur.

96
31. UYGUN YAZILMAYAN BELGELER
Yönetmelik 35. Madde
Resmî yazışmalarda uygulama birliğinin sağlanması amacıyla idareler tarafından hazırlanan veya
teslim alınan belgeler Yönetmelik’e uygunluk açısından incelenmelidir. Herhangi bir madde hükmüne
aykırı hazırlanan bir belge teslim alındığında muhatap cevabî yazıda veya şifahen uyarılmalı,
Yönetmelik’e aykırılığın daha sonra gerçekleştirilen yazışmalarda da devam etmesi durumunda ise
aşağıda örneği verilen yazıyla muhatap uyarılmalıdır: 
MUHATAP 
gg.aa.yyyy tarihli ve …-..….-…..-….. sayılı yazınız Resmî Yazışmalarda Uygulanacak Usul ve
Esaslar Hakkında Yönetmelik’in  ……

---

[K3]
Kaynak: Resmî Yazışma Kılavuzu

len tarih bilgisine ilgide muhakkak yer verilmelidir.
Yanlış Kullanım
Bila tarihli ve E-84801842-902.02-1042582 sayılı
yazınız.
Doğru Kullanım
01.09.2019 
tarihli 
ve 
E-84801842-902.02-
1042582 sayılı yazınız.

Yanlış Kullanım
01.09.2019 tarihli ve 1042582 sayılı yazımız.
Doğru Kullanım
01.09.2019 
tarihli 
ve 
E-84801842-902.02-
1042582 sayılı yazımız.
12.3. İlgi Tutulan Belge Sayısının Yazımı 
İlgi olarak eklenen belgenin sadece kayıt numarası yazılmamalı, belgenin hazırlanma süreci ve ait
olduğu idare/birim bilgisine de erişilebilmesi amacıyla 4 bölümden oluşan sayı, bütünüyle
yazılmalıdır.
28

29
İlgi tutulan belge bilgilerinin
(tarih, sayı ve geldiği idare)
yazılması gerekmektedir. 
Metin kısmında ilk paragrafta ilgi
tutulan belgenin içeriği hakkında
bilgi 
verilerek 
ilgi 
ile 
belge
arasında bağ kurulmalıdır.
İlgide 
yer 
alan 
belge 
muhatap
kurumda bulunmayan bir belge ise ek
olarak gönderilmesi uygun olacaktır.
İlgi 
tutulan 
belge 
kurumların
rahatlıkla Resmî Gazete üzerinden
ulaşabileceği kanun, yönetmelik vb.
ise 
ayrıca 
gönderilmesine 
gerek
yoktur. 

13. METİN
Yönetmelik 16. Madde
Resmî yazılarda esas unsuru teşkil eden ve muhatabın bilgilendirildiği kısım metindir. Metin,
aşağıdaki hususlar dikkate alınarak hazırlanmalıdır:
Açık, anlaşılabilir, kısa ve olabildiğince öz anlatım benimsenmeli,
Herkesçe bilinen Türkçe kelimeler tercih edilmeli,
Türkçe dil bilgisi ve yazım kurallarına uygunluk sağlanmalı (Türk Dil Kurumu Sözlüğü ve Yazım
Kılavuzu dikkate alınmalı

---

[K4]
Kaynak: Resmî Yazışma Kılavuzu

re ismi yer almalıdır. Ayrıca farklı idarelerde
aynı birim adı olabileceğinden karışıklığa yol
açmaması adına idare ismi kullanılmalıdır.
26

12. İLGİ
27
Yönetmelik 15. Madde
İlgi, iki yana yaslı olarak yazılan ve birden fazla olduğunda belgelerin tarih sırasına göre kronolojik
düzenlendiği alandır. İlgide aşağıdaki bilgilerin yer alması gerekmektedir.
12.1.  İlgi Tutulan Belgenin Sahibi İdarenin Yazımı
İlgi Kullanımı
Ticaret Bakanlığının (Personel Genel Müdürlüğü)
01.09.2019 
tarihli 
ve 
E-35799330-902.02-
1042579 sayılı yazısı.
Açıklama
İdare 
dışına 
gönderilen 
belgelerde, 
sadece
“Personel Genel Müdürlüğünün … tarihli ve ...
sayılı yazısı” yazıldığı takdirde, belge sahibinin
hangi idare olduğu anlaşılamayacağından idare
isminin 
(Ticaret 
Bakanlığı) 
yazılması
gerekmektedir.
Yanlış Kullanım
Strateji Geliştirme Daire Başkanlığının 01.09.2019
tarihli E-84801842-902.02-1042580 sayılı yazısı.
Doğru Kullanım
Afyon Kocatepe Üniversitesi Rektörlüğünün
(Strateji Geliştirme Daire Başkanlığı) 01.09.2019
tarihli ve E-84801842-902.02-1042580 sayılı
yazısı.
İlgi tutulan belgelerden yazı içinde bahsedilmelidir. İlgi tutulan belgenin muhatapta olmaması
durumunda, belge muhataba ek olarak iletilmelidir.
İlgi tutulan belge, Resmî Gazete’de yayımlanan bir mevzuat ise ayrıca ek olarak eklenmemelidir. 
12.2. İlgi Tutulan Belge Tarihinin Yazımı
İlgi kısmında vatandaş başvuruları haricinde “bila tarihli” veya “tarihsiz” ifadesi kullanılmamalıdır.
Belgenin görüntüsünden ve üstverisinden erişi

---

[K5]
Kaynak: Resmî Yazışma Kılavuzu

MADDE 15- (1) İlgi, belgenin bağlantılı olduğu diğer belge veya belgelerin
belirtildiği bölümdür.

(2) “İlgi:” yan başlığı, muhatap bölümünün son satırından itibaren iki satır boşluk
bırakılarak ve yazı alanının solundan başlanarak yazılır (Örnek 7).

(3) “Sayı”, “Konu” ve “İlgi” yan başlıklarından sonra kullanılan iki nokta
aynı hizada yazılır (Örnek 7).

(4) İlgide yer alan bilgiler bir satırı geçerse, devamı “İlgi:” yan başlığının ve
sıralamayı gösteren harflerin altı boş bırakılarak alt satıra yazılır (Örnek 7).

(5) İlginin birden fazla olması durumunda, belgeler önceki tarihli olandan
başlanarak tarih sırasına göre sıralanır. Sıralamada, Türk alfabesinde yer alan bütün küçük
harfler, kendilerinden sonra kapama parantez işareti “)” konularak kullanılır (Örnek 7).

(6) İlgide, ilgi tutulan belgeyi gönderen idarenin adı ile belgenin tarihi ve sayısı
belirtilir. Ancak ilgi tutulan belgenin, muhatap idarenin daha önce gönderdiği bir belge
veya muhatap idareye daha önce gönderilen bir belge olması durumunda idare adı
belirtilmez (Örnek 7).

(7) İlgide, “... tarihli ve ... sayılı ...” ibaresi kullanılır ve ilginin sonuna nokta (.)
işareti konulur (Örnek 7).

(8) İlgide belirtilen belge, muhatapta bulunmadığı durumlarda söz konusu belge, ek
olarak muhatabına iletilebilir (Örnek 7).

(9) İlgide belirtilen belge, gerçek kişiden geliyorsa ilgi bölümü “...ın ... tarihli
başvurusu/dilekçesi.” biçiminde yazılır (Örnek 9). Ancak belgenin muhatabı, ilgi tutulan
başvurunun veya dilekçenin sahibi ise ilgi bölümünde gerçek kişinin isim bilgisine yer
verilmez.

(10) Gerçek kişi ve tarih bilgisi bulunmayan başvuru/dilekçe ilgi tutulmak
istendiğinde, ilgi bölümü “İsimsiz ve tarihsiz başvuru/dilekçe.” biçiminde yazılır. Söz
konusu başvurunun/dilekçenin işleme alınıp alınmayacağı ilgili mevzuat hükümlerine göre
değerlendirilir.

«>

işareti

«

Metin

Sadece verilen gerçeklere dayanarak subject ve body üret.

```

**Ham LLM yanıtı**

```text
{
    "subject": "Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi Başvurusu Hk.",
    "body": "Örenli İlçe Kaymakamlığına,\n\nPolat Madencilik adına Pelin Sönmez tarafından Akaryakıt İhalesi Sözleşme Tasarısı Çelişkisi konusunda yapılan ve idari inceleme talep edilen başvurunuz incelenmiştir.\n\nBaşvurunuzun işleme alınmış olduğu bilgilerini rica ederim."
}
```


## Kaliteyi en çok düşüren ilk beş sorun

1. **Yanlış belge türü sözleşmesi:** `ihale_itirazi` DocumentAgent enumunda yoktur; canlıda `dilekce` üretildi ve eksik tarih denetimi atlandı.
2. **Legal bağlam WritingAgent'e taşınmıyor:** LegalAgent'ın 4734 kaynakları veya kanıtları taslak üreticisine hiç verilmedi.
3. **Yönlendirme belirsizliği:** üç farklı profil birimi aynı puan aldı ve `recommended_unit` boş kaldı.
4. **Taslak muhatabı ve söylemi yanlış:** kurum kendine hitap ediyor; “rica ederim” ve başvuru tekrarının kurum cevabı olarak kullanılması gönderime uygun değil.
5. **Extraction/Missing-field yanlışları:** kurum adı adres olarak çıkarıldı, imza tanınmadı; ayrıca uncertain alan WritingAgent'in taslak türü kararını engellemedi.
