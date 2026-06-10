import os
from typing import Optional

from fastapi import Header, HTTPException, UploadFile

PROOFORIGIN_API_KEY = os.getenv("PROOFORIGIN_API_KEY")

MAX_UPLOAD_BYTES = int(os.getenv("PROOFORIGIN_MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".heic",
    ".heif",
    ".gif",
}

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
    "image/gif",
    "application/octet-stream",
}


def api_key_configured() -> bool:
    return bool(PROOFORIGIN_API_KEY)


def is_valid_api_key(api_key: Optional[str]) -> bool:
    if not PROOFORIGIN_API_KEY:
        return True
    return api_key == PROOFORIGIN_API_KEY


def require_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> None:
    if not PROOFORIGIN_API_KEY:
        return

    if not x_api_key or x_api_key != PROOFORIGIN_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Valid X-API-Key header required",
        )


def validate_optional_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> None:
    if not PROOFORIGIN_API_KEY or not x_api_key:
        return

    if x_api_key != PROOFORIGIN_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid X-API-Key header",
        )


def validate_upload_file(file: UploadFile) -> None:
    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Upload filename is required")

    extension = os.path.splitext(filename)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed extensions: {sorted(ALLOWED_EXTENSIONS)}",
        )

    content_type = (file.content_type or "").lower()
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported content type: {content_type}",
        )


async def read_upload_with_limit(file: UploadFile, max_bytes: int = MAX_UPLOAD_BYTES) -> bytes:
    chunks = []
    total = 0

    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break

        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Upload exceeds maximum size of {max_bytes} bytes",
            )

        chunks.append(chunk)

    if total == 0:
        raise HTTPException(status_code=400, detail="Upload file is empty")

    return b"".join(chunks)
