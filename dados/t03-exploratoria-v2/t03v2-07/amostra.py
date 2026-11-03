import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()


def _upload_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR nao definido")
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _normalized_extension(image: Image.Image, original_name: str) -> str:
    fmt = (image.format or "").upper()
    if fmt == "PNG":
        return ".png"
    if fmt in {"JPEG", "JPG"}:
        return ".jpg"

    suffix = Path(original_name).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg"}:
        return ".png" if suffix == ".png" else ".jpg"

    return ".img"


@app.post("/foto")
async def upload_foto(arquivo: UploadFile = File(...)):
    try:
        content = await arquivo.read()
        image = Image.open(io.BytesIO(content))
        image.load()
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Arquivo invalido")
    except Exception:
        raise HTTPException(status_code=400, detail="Arquivo invalido")

    if image.format not in {"PNG", "JPEG"}:
        raise HTTPException(status_code=400, detail="Formato nao suportado")

    ext = _normalized_extension(image, arquivo.filename or "")
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest = _upload_dir() / unique_name

    try:
        dest.write_bytes(content)
    except Exception:
        raise HTTPException(status_code=500, detail="Falha ao salvar arquivo")

    return JSONResponse(status_code=201, content={"arquivo": unique_name})


import io