import os
import re
import uuid
import unicodedata
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

app = FastAPI()


def _get_upload_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR não definido")
    path = Path(base)
    if not path.exists() or not path.is_dir():
        raise RuntimeError("TCC_UPLOAD_DIR inválido")
    return path


UPLOAD_DIR = _get_upload_dir()

_MAX_BYTES = 10 * 1024 * 1024
_ALLOWED_FORMATS = {"PNG": ".png", "JPEG": ".jpg"}
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._ -]+")


def _sanitize_original_name(name: str) -> str:
    name = unicodedata.normalize("NFKC", name).strip()
    name = name.replace("\x00", "")
    name = Path(name).name
    name = _SAFE_NAME_RE.sub("_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name or "arquivo"


def _validate_and_save_image(data: bytes, original_filename: str) -> str:
    if len(data) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Arquivo muito grande",
        )

    try:
        with Image.open(io := __import__("io").BytesIO(data)) as img:
            img.verify()
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido",
        )

    try:
        with Image.open(__import__("io").BytesIO(data)) as img:
            fmt = (img.format or "").upper()
            if fmt not in _ALLOWED_FORMATS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato não suportado",
                )

            ext = _ALLOWED_FORMATS[fmt]
            safe_original = _sanitize_original_name(original_filename)
            stem = Path(safe_original).stem
            unique = uuid.uuid4().hex
            filename = f"{stem}_{unique}{ext}"
            destination = UPLOAD_DIR / filename

            if destination.exists():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Conflito de nome de arquivo",
                )

            with open(destination, "xb") as f:
                f.write(data)

            return filename
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido",
        )


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    content_type = (arquivo.content_type or "").lower()
    if content_type not in {"image/png", "image/jpeg"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de conteúdo não suportado",
        )

    data = await arquivo.read()
    await arquivo.close()

    filename = await run_in_threadpool(
        _validate_and_save_image,
        data,
        arquivo.filename or "arquivo",
    )

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": filename})