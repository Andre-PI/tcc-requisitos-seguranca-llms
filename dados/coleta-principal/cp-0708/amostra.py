import os
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
from PIL.Image import DecompressionBombError

app = FastAPI()

MAX_UPLOAD_SIZE = 2 * 1024 * 1024
MAX_DIMENSION = 1024
ALLOWED_FORMATS = {"PNG": "png", "JPEG": "jpg", "JPG": "jpg"}


def _upload_base_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR não definido")
    return Path(base)


def _safe_server_filename(ext: str) -> str:
    return f"{uuid.uuid4().hex}{ext}"


def _validate_and_load_image(data: bytes) -> tuple[str, Image.Image]:
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo inválido")

    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o limite permitido")

    try:
        img = Image.open(io_bytes := __import__("io").BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError, ValueError, DecompressionBombError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo inválido")

    fmt = (img.format or "").upper()
    if fmt not in ALLOWED_FORMATS:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Formato não suportado")

    if img.width <= 0 or img.height <= 0 or img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Dimensões inválidas")

    return fmt, img


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    filename = arquivo.filename or ""
    ext = Path(filename).suffix.lower()

    if ext not in {".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Extensão não permitida")

    data = await arquivo.read()
    fmt, img = _validate_and_load_image(data)

    if fmt == "JPEG":
        if ext not in {".jpg", ".jpeg"}:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Extensão não permitida")
        ext = ".jpg"
    elif fmt == "PNG":
        if ext != ".png":
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Extensão não permitida")

    base_dir = _upload_base_dir()
    base_dir.mkdir(parents=True, exist_ok=True)

    server_name = _safe_server_filename(ext)
    target_path = (base_dir / server_name).resolve()
    base_resolved = base_dir.resolve()

    if base_resolved != target_path and base_resolved not in target_path.parents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Caminho inválido")

    try:
        save_kwargs = {}
        if fmt == "JPEG":
            save_kwargs.update({"format": "JPEG", "quality": 95, "optimize": False, "progressive": False})
        else:
            save_kwargs.update({"format": "PNG", "optimize": False})

        img.save(str(target_path), **save_kwargs)
    except (OSError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não foi possível salvar o arquivo")

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": server_name})