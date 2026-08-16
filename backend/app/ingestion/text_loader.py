from pathlib import Path


def load_text(path: Path) -> str:
    """
    TXT dosyasını UTF-8 olarak okur.
    """

    return path.read_text(
        encoding="utf-8",
        errors="ignore",
    ).strip()
