import os
import re
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, UploadFile, HTTPException
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


def _safe_extension(filename: str, content_type: str | None) -> str:
    name = filename.lower()
    if name.endswith(".png") or content_type == "image/png":
        return ".png"
    if name.endswith(".jpg") or name.endswith(".jpeg") or content_type == "image/jpeg":
        return ".jpg"
    return ""


@app.post("/foto", status_code=201)
async def upload_foto(arquivo: Annotated[UploadFile, File(...)]):
    ext = _safe_extension(arquivo.filename or "", arquivo.content_type)
    if ext not in {".png", ".jpg"}:
        raise HTTPException(status_code=400, detail="Formato inválido. Envie PNG ou JPEG.")

    base_dir = _upload_dir()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    target = base_dir / unique_name

    try:
        data = await arquivo.read()
        with Image.open(io := __import__("io").BytesIO(data)) as img:
            fmt = (img.format or "").upper()
            if fmt not in {"PNG", "JPEG"}:
                raise HTTPException(status_code=400, detail="Formato inválido. Envie PNG ou JPEG.")
            if fmt == "PNG":
                img.save(target, format="PNG")
            else:
                if img.mode not in ("RGB", "L", "CMYK"):
                    img = img.convert("RGB")
                img.save(target, format="JPEG")
    except HTTPException:
        raise
    except Exception:
        if target.exists():
            try:
                target.unlink()
            except Exception:
                pass
        raise HTTPException(status_code=400, detail="Arquivo de imagem inválido.")

    return JSONResponse(status_code=201, content={"arquivo": unique_name})