import hashlib
import shutil
import subprocess
from pathlib import Path

from .docx_loader import load_docx


def find_soffice() -> Path:
    """
    LibreOffice soffice.exe dosyasını bulur.
    """

    # PATH içerisinde varsa
    soffice_from_path = shutil.which("soffice")

    if soffice_from_path:
        return Path(soffice_from_path)

    # Windows varsayılan kurulum konumları
    candidates = [
        Path(
            r"C:\Program Files\LibreOffice\program\soffice.exe"
        ),
        Path(
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
        ),
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "LibreOffice bulunamadı. "
        "DOC dosyalarının dönüştürülmesi için LibreOffice gerekli."
    )


def convert_doc_to_docx(path: Path) -> Path:
    """
    Eski Microsoft Word .doc dosyasını
    LibreOffice kullanarak .docx formatına dönüştürür.

    Dönüştürülmüş dosyalar cache olarak
    data/processed/converted_docx altında tutulur.
    """

    soffice = find_soffice()

    # Aynı isimli dosyaların çakışmasını önlemek için
    # kaynak yolundan kısa bir hash oluşturuyoruz.
    source_hash = hashlib.sha1(
        str(path.resolve()).encode("utf-8")
    ).hexdigest()[:10]

    output_dir = (
        Path("data/processed/converted_docx")
        / source_hash
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    converted_path = (
        output_dir
        / f"{path.stem}.docx"
    )

    # Daha önce dönüştürüldüyse tekrar dönüştürme.
    if converted_path.exists():
        return converted_path

    command = [
        str(soffice),
        "--headless",
        "--convert-to",
        "docx",
        "--outdir",
        str(output_dir.resolve()),
        str(path.resolve()),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"DOC dönüşümü başarısız: {path.name}\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

    if not converted_path.exists():
        raise RuntimeError(
            f"Dönüştürülmüş DOCX bulunamadı: {path.name}\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

    return converted_path


def load_doc(path: Path) -> str:
    """
    DOC → DOCX → text
    """

    converted_path = convert_doc_to_docx(path)

    return load_docx(converted_path)