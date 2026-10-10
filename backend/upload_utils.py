"""backend/upload_utils.py

Secure upload utilities for AI-Diagnoser:
1. Bounded chunked file reader preventing unbounded memory consumption (SEC-002).
2. Robust filename sanitizer preventing path traversal, control character injection,
   and directory escape attacks (SEC-001).
"""

import os
import re
from typing import Optional
from fastapi import HTTPException, UploadFile, status

# Control characters regex (null bytes, carriage returns, terminal escapes)
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
MAX_FILENAME_LEN = 128


def sanitize_filename(filename: Optional[str], default_name: str = "upload.bin") -> str:
    """Sanitize client-provided filename to prevent path traversal and injection.

    - Strips control characters and null bytes.
    - Normalizes Windows and POSIX path separators.
    - Extracts pure basename, preventing directory traversal (../, ..\\).
    - Replaces dangerous characters with underscores.
    - Truncates excessively long filenames while preserving file extension.
    - Returns safe default if sanitized filename is empty or dangerous.
    """
    if not filename or not isinstance(filename, str):
        return default_name

    # 1. Strip control characters
    clean = _CONTROL_CHAR_RE.sub("", filename).strip()

    # 2. Normalize path separators to forward slash and take basename
    clean = clean.replace("\\", "/")
    base = os.path.basename(clean).strip()

    # 3. Strip leading/trailing dots and spaces to prevent hidden files or traversal artifacts
    base = base.lstrip(". ")
    if not base or base in (".", ".."):
        return default_name

    # 4. Filter characters: allow alphanumeric, dots, dashes, underscores, spaces
    base = re.sub(r"[^\w\.\-\s]", "_", base)

    # 5. Length limit preserving extension
    if len(base) > MAX_FILENAME_LEN:
        name_part, ext_part = os.path.splitext(base)
        max_name_len = MAX_FILENAME_LEN - len(ext_part)
        if max_name_len > 0:
            base = name_part[:max_name_len] + ext_part
        else:
            base = base[:MAX_FILENAME_LEN]

    return base or default_name


async def read_bounded_file(
    file: UploadFile,
    max_bytes: int = 25 * 1024 * 1024,
    chunk_size: int = 65536,
) -> bytes:
    """Asynchronously read file stream in bounded chunks up to max_bytes.

    Aborts immediately and raises HTTP 413 Payload Too Large if size limit is exceeded,
    preventing memory exhaustion and resource starvation. Does not trust Content-Length alone.
    """
    # Fast path: check known file size if reported by underlying spool
    if hasattr(file, "size") and isinstance(file.size, int) and file.size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {max_bytes // (1024 * 1024)} MiB.",
        )

    chunks = []
    total_bytes = 0

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {max_bytes // (1024 * 1024)} MiB.",
            )
        chunks.append(chunk)

    return b"".join(chunks)
