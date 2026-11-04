import os
import re
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

app = FastAPI()

UPLOAD_DIR = Path(os.environ["TCC_UPLOAD_DIR"])
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_filename(name: str) -> str:
    name = os.path.basename(name).strip()
    name = name.replace("\x00", "")
    if not name:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido")

    stem, suffix = os.path.splitext(name)
    suffix = suffix.lower()

    if suffix not in {".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=400, detail="Formato de imagem não समर्थado")

    stem = re.sub(r"[\\/]+", "_", stem).strip()
    if not stem:
        stem = "arquivo"

    unique = uuid.uuid4().hex
    return f"{stem}_{unique}{suffix}"


@app.post("/foto")
async def upload_foto(arquivo: Annotated[UploadFile, File(...)]) -> JSONResponse:
    original_name = arquivo.filename or ""
    saved_name = _sanitize_filename(original_name)
    target_path = UPLOAD_DIR / saved_name

    content = await arquivo.read()
    try:
        with Image.open(io.BytesIO(content)) as img:
            img.verify()
        with Image.open(io.BytesIO(content)) as img:
            fmt = (img.format or "").upper()
            if fmt not in {"PNG", "JPEG"}:
                raise HTTPException(status_code=400, detail="Formato de imagem não suportado")
            img.load()
            img.save(target_path, format=fmt)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Arquivo de imagem inválido")
    finally:
        await arquivo.close()

    return JSONResponse(status_code=201, content={"arquivo": saved_name})


import io