import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

app = FastAPI()

UPLOAD_DIR = Path(os.environ["TCC_UPLOAD_DIR"])
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _safe_filename(original_name: str) -> str:
    suffix = Path(original_name).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=400, detail="Formato de imagem não suportado")
    return f"{uuid.uuid4().hex}{suffix}"


@app.post("/foto")
async def upload_foto(arquivo: UploadFile = File(...)):
    filename = _safe_filename(arquivo.filename or "")
    dest = UPLOAD_DIR / filename

    try:
        data = await arquivo.read()
        with Image.open(io := __import__("io").BytesIO(data)) as img:
            fmt = (img.format or "").upper()
            if fmt not in {"PNG", "JPEG"}:
                raise HTTPException(status_code=400, detail="Formato de imagem não suportado")
            img.load()
            if fmt == "JPEG":
                img.save(dest, format="JPEG")
            else:
                img.save(dest, format="PNG")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Arquivo inválido")

    return JSONResponse(status_code=201, content={"arquivo": filename})