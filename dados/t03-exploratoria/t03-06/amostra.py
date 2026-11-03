import os
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

app = FastAPI()


def _upload_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR não definido")
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sanitize_filename(original_name: str, content_type: str) -> str:
    suffix = ".png" if content_type == "image/png" else ".jpg"
    stem = Path(original_name).stem if original_name else "arquivo"
    stem = stem.strip().replace("\x00", "")
    stem = re.sub(r"[\\/]+", "_", stem)
    stem = stem.replace("..", "_")
    if not stem:
        stem = "arquivo"
    return f"{stem}_{uuid.uuid4().hex}{suffix}"


@app.post("/foto")
async def upload_foto(arquivo: UploadFile = File(...)):
    content_type = (arquivo.content_type or "").lower()
    if content_type not in {"image/png", "image/jpeg"}:
        raise HTTPException(status_code=400, detail="Formato inválido. Envie PNG ou JPEG.")

    try:
        data = await arquivo.read()
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        raise HTTPException(status_code=400, detail="Arquivo de imagem inválido.")

    if img.format not in {"PNG", "JPEG"}:
        raise HTTPException(status_code=400, detail="Formato inválido. Envie PNG ou JPEG.")

    if img.format == "PNG" and content_type != "image/png":
        raise HTTPException(status_code=400, detail="Formato inválido. Envie PNG.")
    if img.format == "JPEG" and content_type != "image/jpeg":
        raise HTTPException(status_code=400, detail="Formato inválido. Envie JPEG.")

    filename = _sanitize_filename(arquivo.filename or "arquivo", content_type)
    output_path = _upload_dir() / filename

    try:
        if img.format == "PNG":
            img.save(output_path, format="PNG")
        else:
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            img.save(output_path, format="JPEG")
    except Exception:
        raise HTTPException(status_code=500, detail="Falha ao salvar arquivo.")

    return JSONResponse(status_code=201, content={"arquivo": filename})


import io