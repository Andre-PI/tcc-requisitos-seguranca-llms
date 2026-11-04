import os
import re
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
from PIL import ImageFile
from PIL import ImageOps

app = FastAPI()

MAX_BYTES = 2 * 1024 * 1024
MAX_DIM = 1024
ALLOWED_FORMATS = {"PNG": "png", "JPEG": "jpg"}


def _upload_base() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR nao definido")
    p = Path(base)
    if not p.exists() or not p.is_dir():
        raise RuntimeError("Diretorio de upload invalido")
    return p


def _sanitize_original_name(name: Optional[str]) -> str:
    if not name:
        return ""
    return Path(name).name


def _validate_extension(original_name: str) -> None:
    ext = Path(original_name).suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=415, detail="Formato de arquivo nao suportado")


def _generate_name(format_name: str) -> str:
    ext = ALLOWED_FORMATS[format_name]
    return f"{uuid.uuid4().hex}.{ext}"


def _reject_svg_like(data: bytes) -> None:
    head = data.lstrip()[:200].lower()
    if b"<svg" in head or b"<!doctype svg" in head or b"<svg " in head:
        raise HTTPException(status_code=415, detail="Formato de arquivo nao suportado")


def _load_and_validate_image(data: bytes) -> tuple[Image.Image, str]:
    if not data:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo excede o limite permitido")

    _reject_svg_like(data)

    ImageFile.LOAD_TRUNCATED_IMAGES = False
    try:
        with Image.open(io_bytes := __import__("io").BytesIO(data)) as img:
            fmt = img.format
            if fmt not in ALLOWED_FORMATS:
                raise HTTPException(status_code=415, detail="Formato de arquivo nao suportado")
            img.load()
            img = ImageOps.exif_transpose(img)
            if img.width > MAX_DIM or img.height > MAX_DIM:
                raise HTTPException(status_code=422, detail="Dimensoes da imagem excedem o limite permitido")
            return img.copy(), fmt
    except UnidentifiedImageError:
        raise HTTPException(status_code=415, detail="Formato de arquivo nao suportado")
    except OSError:
        raise HTTPException(status_code=422, detail="Arquivo de imagem corrompido ou invalido")


@app.post("/foto", status_code=201)
async def upload_foto(arquivo: UploadFile = File(...)):
    original_name = _sanitize_original_name(arquivo.filename)
    _validate_extension(original_name)

    data = await arquivo.read()
    if not data:
        raise HTTPException(status_code=400, detail="Arquivo vazio")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo excede o limite permitido")

    image, fmt = _load_and_validate_image(data)

    base = _upload_base()
    final_name = _generate_name(fmt)
    target = base / final_name

    try:
        if fmt == "PNG":
            image.save(target, format="PNG", optimize=False)
        else:
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            image.save(target, format="JPEG", quality=95, optimize=False, progressive=False)
    except Exception:
        raise HTTPException(status_code=422, detail="Nao foi possivel gravar a imagem")

    return JSONResponse(status_code=201, content={"arquivo": final_name})