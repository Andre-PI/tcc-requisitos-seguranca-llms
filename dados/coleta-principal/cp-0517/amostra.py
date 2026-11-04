from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

app = FastAPI()

UPLOAD_DIR_ENV = "TCC_UPLOAD_DIR"
MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20 MiB
ALLOWED_FORMATS = {"PNG": ".png", "JPEG": ".jpg", "JPG": ".jpg"}
SAFE_NAME_RE = re.compile(r"^[\w\s.\-()À-ÿ\u0080-\uffff]+$", re.UNICODE)


def _get_upload_dir() -> Path:
    base = os.environ.get(UPLOAD_DIR_ENV)
    if not base:
        raise RuntimeError(f"Variável de ambiente {UPLOAD_DIR_ENV} não definida")
    path = Path(base).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir():
        raise RuntimeError(f"{UPLOAD_DIR_ENV} não aponta para um diretório válido")
    return path


def _sanitize_original_name(name: str) -> str:
    name = Path(name).name.strip()
    if not name:
        return "arquivo"
    name = name.replace("\x00", "")
    if len(name) > 180:
        stem = Path(name).stem[:150]
        suffix = Path(name).suffix[:10]
        name = f"{stem}{suffix}"
    return name


def _validate_image_and_get_format(file_path: Path) -> tuple[str, str]:
    try:
        with Image.open(file_path) as img:
            img.verify()
            fmt = (img.format or "").upper()
    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido ou formato não suportado",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível processar a imagem",
        ) from exc

    if fmt not in ALLOWED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas imagens PNG e JPEG são permitidas",
        )

    return fmt, ALLOWED_FORMATS[fmt]


async def _save_upload(upload: UploadFile, dst: Path) -> None:
    size = 0
    try:
        with dst.open("wb") as out:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_IMAGE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Arquivo excede o tamanho máximo permitido",
                    )
                out.write(chunk)
    finally:
        await upload.close()


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    upload_dir = _get_upload_dir()

    original_name = _sanitize_original_name(arquivo.filename or "arquivo")
    ext = Path(original_name).suffix.lower()

    temp_name = f".upload-{uuid.uuid4().hex}.tmp"
    temp_path = upload_dir / temp_name

    await _save_upload(arquivo, temp_path)

    fmt, expected_ext = await run_in_threadpool(_validate_image_and_get_format, temp_path)
    if ext and ext not in {".png", ".jpg", ".jpeg"}:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome do arquivo deve terminar com .png, .jpg ou .jpeg",
        )

    final_ext = expected_ext
    final_name = f"{uuid.uuid4().hex}{final_ext}"
    final_path = upload_dir / final_name

    try:
        with Image.open(temp_path) as img:
            img.load()
            save_kwargs = {}
            if fmt == "JPEG":
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                save_kwargs.update({"format": "JPEG", "quality": 95, "optimize": True, "progressive": True})
            elif fmt == "PNG":
                save_kwargs.update({"format": "PNG", "optimize": True})

            img.save(final_path, **save_kwargs)
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível salvar a imagem",
        ) from exc
    finally:
        temp_path.unlink(missing_ok=True)

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": final_name})