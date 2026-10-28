from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path

from app.core.config import get_settings

SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


def media_root() -> Path:
    settings = get_settings()
    root = Path(settings.media_root)
    if not root.is_absolute():
        # relativo ao backend/
        root = Path(__file__).resolve().parents[3] / root
    root.mkdir(parents=True, exist_ok=True)
    return root


def sanitize_filename(name: str) -> str:
    base = Path(name).name
    cleaned = SAFE_NAME.sub("_", base).strip("._")
    return cleaned[:120] or "file"


def save_bytes(store_id: str, filename: str, content: bytes) -> tuple[str, str, str]:
    """Retorna (storage_key, absolute_path, public_url)."""
    settings = get_settings()
    safe = sanitize_filename(filename)
    key = f"{store_id}/{uuid.uuid4().hex}_{safe}"
    path = media_root() / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    public = f"{settings.media_public_prefix.rstrip('/')}/{key}"
    return key, str(path), public


def delete_key(storage_key: str | None) -> None:
    if not storage_key:
        return
    path = media_root() / storage_key
    if path.is_file():
        path.unlink()


def checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
