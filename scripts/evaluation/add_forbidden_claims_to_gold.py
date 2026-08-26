"""Idempotently add hallucinated-outcome assertions to writing gold records."""

from __future__ import annotations

import json
from pathlib import Path


GOLD_PATH = Path("data/evaluation/writing/gold_taslaklar.jsonl")
DEFAULT_FORBIDDEN_CLAIMS = [
    "Başvurunuz kabul edilmiştir.",
    "Başvurunuz reddedilmiştir.",
    "İşlem tamamlanmıştır.",
    "Talebiniz uygun bulunmuştur.",
    "Başvurunuz uygun görülmüştür.",
    "Değerlendirilmiş ve uygun bulunmuştur.",
    "İhale kararı onanmıştır.",
    "İptal yoluna gidilmeyecektir.",
    "Yardımlar tarafınıza ulaştırılacaktır.",
    "Ruhsatınız düzenlenmiştir.",
    "Ödeme yapılmıştır.",
]


# These legacy gold drafts asserted outcomes that do not occur in their source
# petitions. Keep the correspondence form, but make the result explicitly
# unknown instead of teaching the writer to invent an administrative decision.
UNSUPPORTED_OUTCOME_REPLACEMENTS = {
    "GOLD-0008": (
        "İlgide kayıtlı dilekçeniz ile oğlunuzun yeni ikamet adresiniz "
        "nedeniyle okul naklini talep ettiğiniz anlaşılmıştır. Başvurunun "
        "değerlendirme sonucuna ilişkin doğrulanmış işlem bilgisi "
        "bulunmadığından sonuç bu taslakta belirtilmemiştir."
    ),
    "GOLD-0041": (
        "İlgide kayıtlı dilekçeniz ile ihale belgelerinizin süresinde "
        "sunulduğunu belirterek ihale kararının iptalini ve yeniden "
        "değerlendirme yapılmasını talep ettiğiniz anlaşılmıştır. İtirazın "
        "değerlendirme sonucuna ilişkin doğrulanmış işlem bilgisi "
        "bulunmadığından sonuç bu taslakta belirtilmemiştir."
    ),
    "GOLD-0042": (
        "İlgide kayıtlı dilekçenizde, temizlik hizmetleri ihalesinin teknik "
        "şartnamesindeki asgari personel sayısı kriterine itiraz ederek "
        "şartnamenin düzeltilmesini ve ihalenin ertelenmesini talep ettiğiniz "
        "anlaşılmıştır. İtirazın değerlendirme sonucuna ilişkin doğrulanmış "
        "işlem bilgisi bulunmadığından sonuç bu taslakta belirtilmemiştir."
    ),
    "GOLD-0044": (
        "İlgide kayıtlı dilekçeniz ile kira yardımı ve gıda kolisi desteği "
        "talep ettiğiniz anlaşılmıştır. Başvurunun Mütevelli Heyeti kararına "
        "ilişkin doğrulanmış işlem bilgisi bulunmadığından yardım sonucu bu "
        "taslakta belirtilmemiştir."
    ),
}


def replace_body(text: str, body: str) -> str:
    """Replace only the prose body between the İlgi line and closing phrase."""
    prefix, separator, remainder = text.partition("\n\n    İlgide")
    if not separator:
        raise ValueError("Writing gold body marker not found")
    signer_marker = (
        "\n\n                                                                                          "
        "Ahmet KAYA"
    )
    _, signer_separator, suffix = remainder.partition(signer_marker)
    if not signer_separator:
        raise ValueError("Writing gold signer marker not found")
    return (
        f"{prefix}\n\n    {body}\n    Bilgilerinize sunulur."
        f"{signer_separator}{suffix}"
    )


def upgrade(path: Path = GOLD_PATH) -> list[dict]:
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for record in records:
        record["kullanilmasi_yasak_iddialar"] = list(DEFAULT_FORBIDDEN_CLAIMS)
        safe_body = UNSUPPORTED_OUTCOME_REPLACEMENTS.get(record["id"])
        if safe_body:
            record["taslak_metni"] = replace_body(record["taslak_metni"], safe_body)
            record["notlar"] = (
                "Kaynak evrakta doğrulanmış idari sonuç bulunmadığı için "
                "taslak yalnızca başvuruyu ve sonuç bilgisinin eksikliğini aktarır."
            )
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    return records


def main() -> None:
    records = upgrade()
    print(f"{GOLD_PATH}: {len(records)} kayıt güncellendi")


if __name__ == "__main__":
    main()
