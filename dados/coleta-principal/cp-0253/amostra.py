import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()


def _get_upload_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR nao definido")
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_filename(original_name: str, suffix: str) -> str:
    original_name = Path(original_name).name
    stem = Path(original_name).stem.strip()
    if not stem:
        stem = "foto"
    return f"{stem}_{uuid.uuid4().hex}{suffix}"


@app.post("/foto")
async def upload_foto(arquivo: UploadFile = File(...)):
    upload_dir = _get_upload_dir()

    try:
        data = await arquivo.read()
        if not data:
            raise HTTPException(status_code=400, detail="Arquivo vazio")

        try:
            with Image.open(io_bytes := __import__("io").BytesIO(data)) as img:
                fmt = (img.format or "").upper()
                if fmt not in {"PNG", "JPEG", "JPG"}:
                    raise HTTPException(status_code=415, detail="Formato nao suportado")
                ext = ".png" if fmt == "PNG" else ".jpg"

                saved_name = _safe_filename(arquivo.filename or "foto", ext)
                target = upload_dir / saved_name

                img.save(target, format="PNG" if fmt == "PNG" else "JPEG")
        except UnidentifiedImageError:
            raise HTTPException(status_code=415, detail="Arquivo nao e uma imagem valida")
    finally:
        await arquivo.close()

    return JSONResponse(status_code=201, content={"arquivo": saved_name})