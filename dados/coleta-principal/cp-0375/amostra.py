import os
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
from PIL.Image import DecompressionBombError
from starlette.concurrency import run_in_threadpool

app = FastAPI()

MAX_UPLOAD_SIZE = 2 * 1024 * 1024
MAX_DIMENSION = 1024
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
ALLOWED_FORMATS = {"PNG", "JPEG"}


def _upload_dir() -> Path:
    raw = os.environ.get("TCC_UPLOAD_DIR")
    if not raw:
        raise RuntimeError("TCC_UPLOAD_DIR nao definido")
    base = Path(raw)
    base.mkdir(parents=True, exist_ok=True)
    return base


def _safe_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Formato nao permitido")
    return ".jpg" if suffix == ".jpeg" else suffix


def _validate_image_bytes(data: bytes) -> str:
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio")

    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o limite permitido")

    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt = img.format
            if fmt not in ALLOWED_FORMATS:
                raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Formato nao permitido")
            img.load()
            if img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Dimensoes acima do permitido")
            if fmt == "PNG" and img.mode not in {"1", "L", "LA", "P", "RGB", "RGBA", "I;16", "I", "F"}:
                pass
    except DecompressionBombError:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Imagem excede o limite permitido")
    except UnidentifiedImageError:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Arquivo invalido ou corrompido")
    except OSError:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Arquivo invalido ou corrompido")

    return fmt


def _save_image(data: bytes, fmt: str, suffix: str) -> str:
    base = _upload_dir()
    while True:
        name = f"{uuid.uuid4().hex}{suffix}"
        path = base / name
        if path.exists():
            continue
        try:
            with Image.open(io.BytesIO(data)) as img:
                img.load()
                save_kwargs = {}
                if fmt == "JPEG":
                    if img.mode not in ("RGB", "L"):
                        img = img.convert("RGB")
                    save_kwargs.update({"format": "JPEG", "quality": 95, "optimize": False, "progressive": False})
                else:
                    if img.mode not in ("RGB", "RGBA", "L", "LA", "P", "1"):
                        img = img.convert("RGBA")
                    save_kwargs.update({"format": "PNG", "compress_level": 6})
                img.save(path, **save_kwargs)
            return name
        except Exception:
            if path.exists():
                try:
                    path.unlink()
                except OSError:
                    pass
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nao foi possivel processar a imagem")


import io


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    suffix = _safe_suffix(arquivo.filename or "")
    data = await arquivo.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o limite permitido")
    fmt = await run_in_threadpool(_validate_image_bytes, data)
    if (fmt == "PNG" and suffix != ".png") or (fmt == "JPEG" and suffix not in {".jpg", ".jpeg"}):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Extensao nao corresponde ao conteudo")
    saved_name = await run_in_threadpool(_save_image, data, fmt, suffix)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": saved_name})