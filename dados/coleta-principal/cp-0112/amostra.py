import os
import re
import uuid
import imghdr
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

_UPLOAD_DIR_ENV = "TCC_UPLOAD_DIR"
_MAX_BYTES = 10 * 1024 * 1024  # 10 MiB
_ALLOWED_FORMATS = {"PNG": ".png", "JPEG": ".jpg", "JPG": ".jpg"}
_SAFE_NAME_RE = re.compile(r"^[\w.\- ]+$", re.UNICODE)


def _get_upload_dir() -> Path:
    raw = os.environ.get(_UPLOAD_DIR_ENV)
    if not raw:
        raise RuntimeError(f"Environment variable {_UPLOAD_DIR_ENV} is not set")
    base = Path(raw).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    if not base.is_dir():
        raise RuntimeError(f"{_UPLOAD_DIR_ENV} must point to a directory")
    return base


def _sanitize_filename(name: str) -> str:
    name = Path(name).name.strip()
    if not name:
        return ""

    if not _SAFE_NAME_RE.fullmatch(name):
        return ""

    return name


def _detect_image_format(data: bytes) -> str | None:
    try:
        with Image.open(io := __import__("io").BytesIO(data)) as img:
            fmt = (img.format or "").upper()
            if fmt in _ALLOWED_FORMATS:
                img.verify()
                return fmt
    except (UnidentifiedImageError, OSError, ValueError):
        return None
    return None


def _make_filename(original_name: str, image_format: str) -> str:
    ext = _ALLOWED_FORMATS[image_format]
    sanitized = _sanitize_filename(original_name)
    stem = Path(sanitized).stem if sanitized else ""
    if not stem:
        stem = f"upload-{uuid.uuid4().hex}"
    stem = stem[:120].rstrip(" .")
    if not stem:
        stem = f"upload-{uuid.uuid4().hex}"
    return f"{stem}{ext}"


@app.post("/foto")
async def upload_foto(arquivo: Annotated[UploadFile, File(...)]) -> JSONResponse:
    if not arquivo.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo inválido")

    content = await arquivo.read(_MAX_BYTES + 1)
    await arquivo.close()

    if not content or len(content) > _MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo muito grande")

    image_format = _detect_image_format(content)
    if image_format is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato inválido")

    try:
        with Image.open(__import__("io").BytesIO(content)) as img:
            img.load()
            if (img.format or "").upper() != image_format:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato inválido")
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato inválido")

    upload_dir = _get_upload_dir()
    filename = _make_filename(arquivo.filename, image_format)
    target = upload_dir / filename

    if target.exists():
        stem = target.stem
        suffix = target.suffix
        filename = f"{stem}-{uuid.uuid4().hex}{suffix}"
        target = upload_dir / filename

    try:
        with open(target, "xb") as f:
            f.write(content)
    except FileExistsError:
        filename = f"{Path(filename).stem}-{uuid.uuid4().hex}{Path(filename).suffix}"
        target = upload_dir / filename
        with open(target, "xb") as f:
            f.write(content)
    except OSError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao salvar arquivo")

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": filename})