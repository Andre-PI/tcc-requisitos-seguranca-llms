import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image

app = FastAPI()


def _upload_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR não definida")
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_filename(original: str, content_type: str) -> str:
    suffix = ""
    if content_type == "image/png":
        suffix = ".png"
    elif content_type == "image/jpeg":
        suffix = ".jpg"

    stem = Path(original).name
    if not stem or stem in {".", ".."}:
        stem = "arquivo"

    name = f"{stem}_{uuid.uuid4().hex}{suffix}"
    return name


@app.post("/foto")
async def upload_foto(arquivo: UploadFile = File(...)):
    if arquivo.content_type not in {"image/png", "image/jpeg"}:
        raise HTTPException(status_code=400, detail="Formato inválido")

    try:
        data = await arquivo.read()
        with Image.open(io := __import__("io").BytesIO(data)) as img:
            img.verify()

        io2 = __import__("io").BytesIO(data)
        with Image.open(io2) as img:
            img.load()
            fmt = "PNG" if arquivo.content_type == "image/png" else "JPEG"
            filename = _safe_filename(arquivo.filename or "arquivo", arquivo.content_type)
            out_path = _upload_dir() / filename
            img.save(out_path, format=fmt)
    except Exception:
        raise HTTPException(status_code=400, detail="Arquivo de imagem inválido")
    finally:
        await arquivo.close()

    return JSONResponse(status_code=201, content={"arquivo": filename})