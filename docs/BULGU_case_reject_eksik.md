# Bulgu: CaseDraft reddetme yaşam döngüsü eksik

Mevcut Case API ve `CaseEngine`, taslak kaydetme, düzenleme ve onaylama
işlemlerini destekliyor; ancak taslak reddetme endpoint'i, engine işlemi veya
`DRAFT_REJECTED` eventi bulunmuyor.

Bu nedenle field-level audit çalışması mevcut onay ve yönlendirme işlemlerini
kapsar. Reddetme davranışı P1 zincir/audit kapsamına yeni bir API sözleşmesi
eklenmeden dahil edilmemelidir.

İleride ele alınırken en az şu kararlar açıkça tanımlanmalıdır:

- Reddetme yetkisine sahip roller.
- İzin verilen draft ve Case durumları.
- Zorunlu ret gerekçesi ve yeniden düzenleme geçişi.
- `before_value` / `after_value` audit sözleşmesi.
- Bildirim ve vatandaş görünürlüğü.
