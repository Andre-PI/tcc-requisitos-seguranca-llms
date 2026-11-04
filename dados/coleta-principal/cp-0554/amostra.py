import os
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

app = FastAPI()

UPLOAD_DIR = os.environ.get("TCC_UPLOAD_DIR")
if not UPLOAD_DIR:
    raise RuntimeError("TCC_UPLOAD_DIR não definido no ambiente")

BASE_DIR = Path(UPLOAD_DIR)
BASE_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}


def _sanitize_filename(name: str) -> str:
    name = Path(name).name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._-")
    return name or "arquivo"


def _validate_image(path: Path) -> None:
    try:
        with Image.open(path) as img:
            img.verify()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Arquivo inválido") from exc


@app.post("/foto")
async def enviar_foto(arquivo: UploadFile = File(...)):
    original = _sanitize_filename(arquivo.filename or "arquivo")
    suffix = Path(original).suffix.lower()

    if suffix not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail="Formato não समर्थado")

    nome_salvo = f"{uuid.uuid4().hex}{suffix}"
    destino = BASE_DIR / nome_salvo

    try:
        with destino.open("wb") as f:
            while True:
                chunk = await arquivo.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
    except Exception as exc:
        if destino.exists():
            destino.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Falha ao salvar arquivo") from exc
    finally:
        await arquivo.close()

    _validate_image(destino)

    return JSONResponse(status_code=201, content={"arquivo": nome_salvo})