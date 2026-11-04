import os
import re
import uuid
import io
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

MAX_UPLOAD_SIZE = 2 * 1024 * 1024
MAX_DIMENSION = 1024
ALLOWED_FORMATS = {"PNG": "png", "JPEG": "jpg", "JPG": "jpg"}


def _upload_base_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR nao definido")
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def _safe_extension(filename: str) -> str | None:
    suffix = Path(filename).suffix.lower().lstrip(".")
    if suffix in {"png", "jpg", "jpeg"}:
        return suffix
    return None


def _validate_and_load_image(data: bytes) -> tuple[Image.Image, str]:
    if not data:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo excede o limite de 2 MiB")

    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except UnidentifiedImageError:
        raise HTTPException(status_code=415, detail="Formato de imagem nao suportado")
    except Exception:
        raise HTTPException(status_code=422, detail="Imagem corrompida ou invalida")

    if img.format not in ALLOWED_FORMATS:
        raise HTTPException(status_code=415, detail="Formato de imagem nao suportado")

    if img.width <= 0 or img.height <= 0 or img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
        raise HTTPException(status_code=422, detail="Dimensoes da imagem fora do limite")

    if img.format == "JPEG" and img.mode not in ("RGB", "L", "CMYK", "YCbCr"):
        img = img.convert("RGB")
    elif img.format == "PNG" and img.mode not in ("RGB", "RGBA", "L", "LA", "P"):
        img = img.convert("RGBA")

    return img, ALLOWED_FORMATS[img.format]


@app.post("/foto", status_code=201)
async def upload_foto(arquivo: UploadFile = File(...)):
    ext = _safe_extension(arquivo.filename or "")
    if ext is None:
        raise HTTPException(status_code=415, detail="Extensao nao permitida")

    data = await arquivo.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo excede o limite de 2 MiB")

    img, fmt_ext = _validate_and_load_image(data)

    base_dir = _upload_base_dir()
    name = f"{uuid.uuid4().hex}.{fmt_ext}"
    final_path = (base_dir / name).resolve()

    if base_dir != final_path.parent and base_dir not in final_path.parents:
        raise HTTPException(status_code=400, detail="Caminho invalido")

    try:
        save_kwargs = {}
        if img.format == "JPEG":
            save_kwargs.update({"format": "JPEG", "quality": 95, "optimize": False, "progressive": False})
        elif img.format == "PNG":
            save_kwargs.update({"format": "PNG", "compress_level": 6})
        else:
            raise HTTPException(status_code=415, detail="Formato de imagem nao suportado")

        img.save(final_path, **save_kwargs)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=422, detail="Falha ao salvar a imagem")

    return JSONResponse(status_code=201, content={"arquivo": name})