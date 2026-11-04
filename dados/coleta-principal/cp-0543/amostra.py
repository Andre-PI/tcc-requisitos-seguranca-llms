import os
import re
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

MAX_UPLOAD_SIZE = 2_097_152  # 2 MiB
MAX_DIMENSION = 1024
ALLOWED_FORMATS = {"PNG", "JPEG"}
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def _get_upload_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR nao definido")
    return Path(base)


def _safe_ext(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".jpeg":
        return ".jpg"
    return suffix


def _validate_and_decode_image(data: bytes) -> tuple[str, Image.Image]:
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="arquivo vazio")

    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="arquivo excede o limite permitido")

    try:
        with Image.open(BytesIO(data)) as img:
            img.load()
            fmt = (img.format or "").upper()
            if fmt not in ALLOWED_FORMATS:
                raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="formato nao suportado")
            if img.width <= 0 or img.height <= 0 or img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="dimensoes invalidas")
            return fmt, img.copy()
    except UnidentifiedImageError:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="arquivo nao e uma imagem valida")
    except OSError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="arquivo corrompido ou invalido")


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    upload_dir = _get_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = _safe_ext(arquivo.filename or "")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="extensao nao permitida")

    data = await arquivo.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="arquivo excede o limite permitido")

    fmt, image = _validate_and_decode_image(data)

    if fmt == "JPEG" and image.mode not in ("RGB", "L", "CMYK", "YCbCr"):
        image = image.convert("RGB")
    elif fmt == "PNG" and image.mode in ("P", "PA"):
        image = image.convert("RGBA")

    server_name = f"{uuid.uuid4().hex}{ext}"
    target = (upload_dir / server_name).resolve(strict=False)
    base_resolved = upload_dir.resolve(strict=False)
    if base_resolved not in target.parents and target != base_resolved:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="caminho invalido")

    save_kwargs = {}
    if fmt == "JPEG":
        save_kwargs.update({"format": "JPEG", "quality": 95, "optimize": False, "progressive": False})
    else:
        save_kwargs.update({"format": "PNG", "optimize": False})

    buffer = BytesIO()
    image.save(buffer, **save_kwargs)
    output = buffer.getvalue()

    if len(output) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="arquivo excede o limite permitido")

    with open(target, "xb") as f:
        f.write(output)

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": server_name})