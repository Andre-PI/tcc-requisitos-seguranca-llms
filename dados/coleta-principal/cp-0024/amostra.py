import os
import re
import uuid
from pathlib import Path
from typing import Final

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image

app = FastAPI()

UPLOAD_DIR_ENV: Final[str] = "TCC_UPLOAD_DIR"
ALLOWED_IMAGE_FORMATS: Final[set[str]] = {"JPEG", "PNG", "GIF", "WEBP", "BMP", "TIFF"}


def _get_upload_dir() -> Path:
    raw = os.environ.get(UPLOAD_DIR_ENV)
    if not raw:
        raise RuntimeError(f"Environment variable {UPLOAD_DIR_ENV} is not set")
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_filename(original_name: str, image_format: str) -> str:
    stem = Path(original_name).stem if original_name else "foto"
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    if not stem:
        stem = "foto"
    ext = {
        "JPEG": ".jpg",
        "PNG": ".png",
        "GIF": ".gif",
        "WEBP": ".webp",
        "BMP": ".bmp",
        "TIFF": ".tiff",
    }.get(image_format.upper(), ".img")
    return f"{stem}_{uuid.uuid4().hex}{ext}"


@app.post("/foto", status_code=201)
async def enviar_foto(arquivo: UploadFile = File(...)):
    upload_dir = _get_upload_dir()

    try:
        contents = await arquivo.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Arquivo vazio")

        with Image.open(io := __import__("io").BytesIO(contents)) as img:
            img.load()
            image_format = (img.format or "").upper()
            if image_format not in ALLOWED_IMAGE_FORMATS:
                raise HTTPException(status_code=400, detail="Formato de imagem não समर्थado")

        nome_salvo = _safe_filename(arquivo.filename or "foto", image_format)
        destino = upload_dir / nome_salvo
        with open(destino, "wb") as f:
            f.write(contents)

        return JSONResponse(status_code=201, content={"arquivo": nome_salvo})
    finally:
        await arquivo.close()