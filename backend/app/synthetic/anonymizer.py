import re


def anonymize_basic_pii(text: str) -> str:
    """
    Temel kişisel veri kalıplarını maskeler.
    """

    # TC Kimlik No benzeri 11 haneli sayılar
    text = re.sub(
        r"(?<!\d)\d{11}(?!\d)",
        "[TC_KIMLIK_NO]",
        text,
    )

    # E-posta
    text = re.sub(
        r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
        "[EPOSTA]",
        text,
    )

    # Türkiye cep telefonu numarası
    text = re.sub(
        r"(?<!\d)(?:\+90|0090|0)?5\d{9}(?!\d)",
        "[TELEFON]",
        text,
    )

    return text