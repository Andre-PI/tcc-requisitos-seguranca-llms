import os
import re
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_DIMENSION = 1024
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def _upload_base_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR não definido")
    return Path(base)


def _safe_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return suffix if suffix in ALLOWED_EXTENSIONS else ""


def _validate_image(data: bytes, original_filename: str) -> str:
    if not data:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo excede o limite de tamanho")

    suffix = _safe_suffix(original_filename)
    if not suffix:
        raise HTTPException(status_code=415, detail="Formato não suportado")

    try:
        with Image.open(BytesIO(data)) as img:
            img.load()
            fmt = (img.format or "").upper()
            width, height = img.size
    except UnidentifiedImageError:
        raise HTTPException(status_code=415, detail="Arquivo não é uma imagem válida")
    except Exception:
        raise HTTPException(status_code=422, detail="Arquivo de imagem corrompido")

    if fmt not in {"PNG", "JPEG"}:
        raise HTTPException(status_code=415, detail="Formato não suportado")

    if width <= 0 or height <= 0 or width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise HTTPException(status_code=422, detail="Dimensões inválidas")

    if fmt == "PNG" and suffix != ".png":
        raise HTTPException(status_code=415, detail="Extensão não permitida para PNG")
    if fmt == "JPEG" and suffix not in {".jpg", ".jpeg"}:
        raise HTTPException(status_code=415, detail="Extensão não permitida para JPEG")

    return ".png" if fmt == "PNG" else ".jpg"


@app.post("/foto", status_code=201)
async def upload_foto(arquivo: UploadFile = File(...)):
    raw = await arquivo.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo excede o limite de tamanho")

    try:
        ext = _validate_image(raw, arquivo.filename or "")
        base_dir = _upload_base_dir()
        base_dir.mkdir(parents=True, exist_ok=True)

        for _ in range(10):
            name = f"{uuid.uuid4().hex}{ext}"
            target = base_dir / name
            if not target.exists():
                with open(target, "xb") as f:
                    f.write(raw)
                return JSONResponse(status_code=201, content={"arquivo": name})

        raise HTTPException(status_code=500, detail="Falha ao gerar nome de arquivo")
    finally:
        await arquivo.close()