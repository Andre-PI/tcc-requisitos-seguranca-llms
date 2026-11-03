from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

UPLOAD_DIR_ENV = "TCC_UPLOAD_DIR"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MiB
ALLOWED_FORMATS = {"PNG": ".png", "JPEG": ".jpg"}

_INVALID_FILENAME_CHARS = re.compile(r"[\x00-\x1f\x7f/\\]")


def _get_upload_dir() -> Path:
    raw = os.environ.get(UPLOAD_DIR_ENV)
    if not raw:
        raise RuntimeError(f"Environment variable {UPLOAD_DIR_ENV} is not defined")
    base = Path(raw).expanduser()
    if not base.exists() or not base.is_dir():
        raise RuntimeError(f"{UPLOAD_DIR_ENV} must point to an existing directory")
    return base.resolve()


def _sanitize_original_name(name: str) -> str:
    name = name.strip()
    if not name:
        return "arquivo"
    name = _INVALID_FILENAME_CHARS.sub("_", name)
    return name[:180] or "arquivo"


def _unique_filename(base_dir: Path, original_name: str, ext: str) -> str:
    stem = Path(original_name).stem or "arquivo"
    stem = _sanitize_original_name(stem)
    candidate = f"{stem}{ext}"
    if not (base_dir / candidate).exists():
        return candidate

    for _ in range(1000):
        candidate = f"{stem}-{uuid.uuid4().hex}{ext}"
        if not (base_dir / candidate).exists():
            return candidate

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Não foi possível gerar um nome de arquivo único",
    )


def _validate_and_save_image(upload: UploadFile, base_dir: Path) -> str:
    if not upload.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido",
        )

    try:
        upload.file.seek(0)
        with Image.open(upload.file) as img:
            img.verify()
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de imagem não suportado",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido",
        )

    try:
        upload.file.seek(0)
        with Image.open(upload.file) as img:
            fmt = (img.format or "").upper()
            if fmt not in ALLOWED_FORMATS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Somente imagens PNG e JPEG são aceitas",
                )

            ext = ALLOWED_FORMATS[fmt]
            safe_name = _unique_filename(base_dir, upload.filename, ext)
            target_path = base_dir / safe_name
            tmp_path = base_dir / f".{safe_name}.tmp-{uuid.uuid4().hex}"

            upload.file.seek(0)
            total = 0
            with open(tmp_path, "wb") as out:
                while True:
                    chunk = upload.file.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_UPLOAD_BYTES:
                        try:
                            tmp_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="Arquivo excede o tamanho máximo permitido",
                        )
                    out.write(chunk)

            os.replace(tmp_path, target_path)
            return safe_name

    finally:
        try:
            upload.file.close()
        except Exception:
            pass


@app.post("/foto")
async def upload_foto(arquivo: UploadFile = File(...)):
    try:
        base_dir = _get_upload_dir()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    saved_name = _validate_and_save_image(arquivo, base_dir)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"arquivo": saved_name},
    )