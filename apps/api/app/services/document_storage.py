import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings

settings = get_settings()
CHUNK_SIZE = 1024 * 1024


class DocumentTooLargeError(ValueError):
    pass


def storage_root() -> Path:
    root = Path(settings.document_storage_path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


async def save_upload(upload: UploadFile) -> tuple[str, int]:
    suffix = Path(upload.filename or "document").suffix.lower()[:16]
    storage_key = f"{uuid.uuid4().hex}{suffix}"
    target = storage_root() / storage_key
    max_bytes = settings.document_max_upload_mb * 1024 * 1024
    total = 0

    try:
        with target.open("wb") as stream:
            while True:
                chunk = await upload.read(CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise DocumentTooLargeError(
                        f"Document exceeds the {settings.document_max_upload_mb} MB upload limit"
                    )
                stream.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    return storage_key, total


def document_path(storage_key: str) -> Path:
    root = storage_root()
    candidate = (root / storage_key).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("Invalid document storage key")
    return candidate
