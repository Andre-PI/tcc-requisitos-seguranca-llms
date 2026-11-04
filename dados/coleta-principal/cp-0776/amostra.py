import os
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

UPLOAD_DIR = os.environ.get("TCC_UPLOAD_DIR")
if not UPLOAD_DIR:
    raise RuntimeError("TCC_UPLOAD_DIR must be defined before importing this module")

BASE_DIR = Path(UPLOAD_DIR)
BASE_DIR.mkdir(parents=True, exist_ok=True)


def _safe_filename(original_name: str) -> str:
    suffix = Path(original_name).suffix.lower()
    return f"{uuid4().hex}{suffix}"


@app.post("/foto")
async def enviar_foto(arquivo: UploadFile = File(...)):
    filename = _safe_filename(arquivo.filename or "arquivo")
    destino = BASE_DIR / filename

    try:
        conteúdo = await arquivo.read()
        if not conteúdo:
            raise HTTPException(status_code=400, detail="Arquivo vazio")

        with Image.open(__import__("io").BytesIO(conteúdo)) as img:
            img.verify()

        destino.write_bytes(conteúdo)
        return JSONResponse(status_code=201, content={"arquivo": filename})

    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Arquivo inválido")
    finally:
        await arquivo.close()