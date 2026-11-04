import os
import re
import uuid
from pathlib import Path
from typing import Final

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
from PIL.Image import DecompressionBombError

app = FastAPI()

MAX_UPLOAD_SIZE: Final[int] = 2 * 1024 * 1024
MAX_DIMENSION: Final[int] = 1024
ALLOWED_FORMATS: Final[set[str]] = {"PNG", "JPEG"}
ALLOWED_EXTENSIONS: Final[set[str]] = {".png", ".jpg", ".jpeg"}

_IMAGE_EXT_RE = re.compile(r"(?i)\.(png|jpe?g)$")


def _upload_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR nao definida")
    return Path(base)


def _safe_generated_name(fmt: str) -> str:
    ext = ".png" if fmt == "PNG" else ".jpg"
    return f"{uuid.uuid4().hex}{ext}"


def _validate_and_load_image(data: bytes) -> tuple[Image.Image, str]:
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio")

    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o limite de 2 MiB")

    try:
        with Image.open(io_bytes := __import__("io").BytesIO(data)) as img:
            fmt = (img.format or "").upper()
            if fmt not in ALLOWED_FORMATS:
                raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Formato de imagem nao suportado")

            img.load()

            width, height = img.size
            if width <= 0 or height <= 0 or width > MAX_DIMENSION or height > MAX_DIMENSION:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Dimensoes invalidas")

            if fmt == "PNG":
                if img.mode not in {"1", "L", "LA", "P", "RGB", "RGBA", "I;16", "I", "CMYK", "YCbCr"}:
                    img = img.convert("RGBA")
            else:
                if img.mode not in {"L", "RGB", "CMYK", "YCbCr"}:
                    img = img.convert("RGB")

            return img.copy(), fmt
    except DecompressionBombError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Imagem invalida")
    except UnidentifiedImageError:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Conteudo nao e uma imagem PNG ou JPEG valida")
    except OSError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Arquivo de imagem corrompido ou invalido")


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    filename = arquivo.filename or ""
    if not _IMAGE_EXT_RE.search(filename):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Extensao nao permitida")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Extensao nao permitida")

    data = await arquivo.read()
    img, fmt = _validate_and_load_image(data)

    out_dir = _upload_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    if fmt == "JPEG":
        if img.mode not in {"L", "RGB"}:
            img = img.convert("RGB")
    elif fmt == "PNG":
        if img.mode == "P":
            img = img.convert("RGBA")

    while True:
        saved_name = _safe_generated_name(fmt)
        target = out_dir / saved_name
        try:
            with target.open("xb") as f:
                save_kwargs = {"format": fmt}
                if fmt == "JPEG":
                    save_kwargs.update({"quality": 95, "optimize": False, "progressive": False})
                img.save(f, **save_kwargs)
            break
        except FileExistsError:
            continue

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": saved_name})