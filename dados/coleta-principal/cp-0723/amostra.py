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
        raise RuntimeError("TCC_UPLOAD_DIR nao definido")
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _guess_extension(fmt: str | None, original_name: str) -> str:
    fmt = (fmt or "").upper()
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
        img = Image.open(io.BytesIO(content))
        img.load()
    except Exception:
        raise HTTPException(status_code=400, detail="Arquivo invalido")

    fmt = img.format
    if fmt not in {"PNG", "JPEG"}:
        raise HTTPException(status_code=415, detail="Formato nao suportado")

    base_dir = _upload_dir()
    ext = _guess_extension(fmt, arquivo.filename or "")

    original_stem = Path(arquivo.filename or "arquivo").stem
    safe_name = f"{original_stem}_{uuid.uuid4().hex}{ext}"
    target = base_dir / safe_name

    if fmt == "PNG":
        img.save(target, format="PNG")
    else:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.save(target, format="JPEG", quality=95, optimize=False)

    return JSONResponse(status_code=201, content={"arquivo": safe_name})


import io