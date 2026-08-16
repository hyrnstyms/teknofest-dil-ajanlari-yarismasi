import random


NAMES = [
    "Elif Karaca",
    "Mert Aydın",
    "Zeynep Demir",
    "Emre Kaya",
    "Buse Şahin",
    "Can Yıldız",
    "Selin Arslan",
    "Kerem Koç",
    "Ece Aksoy",
    "Burak Çetin",
]


ADDRESSES = [
    "Örnek Mahallesi Çınar Sokak No: 18 Ankara",
    "Yeni Mahalle Pınar Caddesi No: 24 Bursa",
    "Cumhuriyet Mahallesi Lale Sokak No: 11 İzmir",
    "Bahçelievler Mahallesi Güneş Sokak No: 7 Eskişehir",
    "Atatürk Mahallesi Deniz Caddesi No: 32 Sakarya",
]


PHONES = [
    "0500 000 00 01",
    "0500 000 00 02",
    "0500 000 00 03",
    "0500 000 00 04",
    "0500 000 00 05",
]


EMAILS = [
    "elif.karaca@example.com",
    "mert.aydin@example.com",
    "zeynep.demir@example.com",
    "emre.kaya@example.com",
    "buse.sahin@example.com",
]


DATES = [
    "03.08.2026",
    "05.08.2026",
    "07.08.2026",
    "10.08.2026",
    "12.08.2026",
    "14.08.2026",
]


WRONG_INSTITUTIONS = [
    "İl Sağlık Müdürlüğü",
    "Belediye Başkanlığı",
    "Kaymakamlık",
    "Üniversite Rektörlüğü",
    "İl Millî Eğitim Müdürlüğü",
]


def random_person() -> dict:
    return {
        "name": random.choice(NAMES),
        "address": random.choice(ADDRESSES),
        "phone": random.choice(PHONES),
        "email": random.choice(EMAILS),
        "date": random.choice(DATES),
    }


def different_name(current_name: str) -> str:
    candidates = [
        name
        for name in NAMES
        if name != current_name
    ]

    return random.choice(candidates)


def wrong_institution(
    correct_institution: str,
) -> str:

    candidates = [
        institution
        for institution in WRONG_INSTITUTIONS
        if institution.lower()
        not in correct_institution.lower()
    ]

    return random.choice(candidates)