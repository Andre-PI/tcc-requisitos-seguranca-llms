import os
import re
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_DIMENSION = 1024
ALLOWED_FORMATS = {"PNG": "png", "JPEG": "jpg", "JPG": "jpg"}


def _upload_dir() -> Path:
    base = os.getenv("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR nao configurada")
    path = Path(base)
    if not path.exists() or not path.is_dir():
        raise RuntimeError("Diretorio de upload invalido")
    return path.resolve()


def _safe_extension(filename: str) -> str | None:
    suffix = Path(filename).suffix.lower()
    if suffix in {".png"}:
        return "png"
    if suffix in {".jpg", ".jpeg"}:
        return "jpg"
    return None


def _validate_and_load_image(data: bytes) -> tuple[Image.Image, str]:
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o limite permitido")

    try:
        img = Image.open(BytesIO(data))
        img.load()
    except UnidentifiedImageError:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Formato de imagem nao suportado")
    except Exception:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Arquivo de imagem invalido")

    fmt = (img.format or "").upper()
    if fmt not in ALLOWED_FORMATS:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Apenas PNG e JPEG sao aceitos")

    if img.width <= 0 or img.height <= 0 or img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Dimensoes da imagem invalidas")

    return img, ALLOWED_FORMATS[fmt]


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    ext = _safe_extension(arquivo.filename or "")
    if ext is None:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Extensao nao permitida")

    data = await arquivo.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o limite permitido")

    img, detected_ext = _validate_and_load_image(data)
    if ext != detected_ext:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Extensao nao corresponde ao conteudo")

    upload_dir = _upload_dir()
    filename = f"{uuid.uuid4().hex}.{detected_ext}"
    target = upload_dir / filename

    try:
        if detected_ext == "png":
            img.save(target, format="PNG")
        else:
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            elif img.mode == "L":
                img = img.convert("RGB")
            img.save(target, format="JPEG", quality=95, optimize=False)
    except Exception:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nao foi possivel salvar a imagem")

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": filename})