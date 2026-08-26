import hashlib
import re
import unicodedata
import uuid


def normalize_chunk_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(text or ""))
    return re.sub(r"\s+", " ", normalized).strip()


def deterministic_point_id(
    source_id: str,
    madde_no: str,
    chunk_index: int | str,
    text: str,
) -> str:
    text_hash = hashlib.sha256(
        normalize_chunk_text(text).encode("utf-8")
    ).hexdigest()
    identity = "|".join(
        (
            "kamuai:v2",
            str(source_id).strip(),
            str(madde_no).strip(),
            str(chunk_index),
            text_hash,
        )
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, identity))


def legacy_eval_point_id(source_id: str, madde_no: str) -> str:
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"kamuai_eval:{source_id}:{madde_no}",
        )
    )
