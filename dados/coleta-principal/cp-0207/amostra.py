import os
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

app = FastAPI()

UPLOAD_DIR = Path(os.environ.get("TCC_UPLOAD_DIR", "")).expanduser()


def _safe_filename(original_name: str) -> str:
    name = Path(original_name).name.strip()
    if not name:
        name = "foto"

    stem = Path(name).stem.strip()
    suffix = Path(name).suffix.lower()

    if suffix not in {".png", ".jpg", ".jpeg"}:
        suffix = ".png"

    stem = re.sub(r"[\x00-\x1f\x7f]", "", stem).strip()
    stem = stem.replace("/", "_").replace("\\", "_")
    if not stem:
        stem = "foto"

    unique = uuid.uuid4().hex
    return f"{stem}_{unique}{suffix}"


@app.post("/foto")
async def upload_foto(arquivo: UploadFile = File(...)):
    if not UPLOAD_DIR:
        raise HTTPException(status_code=500, detail="TCC_UPLOAD_DIR não definido")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    content = await arquivo.read()
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    try:
        with Image.open(io := __import__("io").BytesIO(content)) as img:
            img.load()
            fmt = (img.format or "").upper()
            if fmt not in {"PNG", "JPEG"}:
                raise HTTPException(status_code=415, detail="Formato não suportado")
            ext = ".png" if fmt == "PNG" else ".jpg"
            filename = _safe_filename(arquivo.filename or f"foto{ext}")
            if Path(filename).suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                filename = f"{Path(filename).stem}{ext}"
            target = UPLOAD_DIR / filename
            if target.exists():
                filename = _safe_filename(arquivo.filename or f"foto{ext}")
                if Path(filename).suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                    filename = f"{Path(filename).stem}{ext}"
                target = UPLOAD_DIR / filename
            target.write_bytes(content)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Arquivo inválido")

    return JSONResponse(status_code=201, content={"arquivo": target.name})