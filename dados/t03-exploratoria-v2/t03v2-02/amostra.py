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
    raise RuntimeError("TCC_UPLOAD_DIR must be defined before importing this module")

BASE_DIR = Path(UPLOAD_DIR)
BASE_DIR.mkdir(parents=True, exist_ok=True)

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_filename(name: str) -> str:
    name = Path(name).name.strip()
    name = _SAFE_NAME_RE.sub("_", name)
    name = name.strip("._")
    return name or "arquivo"


def _guess_extension(upload: UploadFile) -> str:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix in _ALLOWED_EXTENSIONS:
        return suffix
    content_type = (upload.content_type or "").lower()
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
    }
    return mapping.get(content_type, "")


def _validate_image(path: Path) -> None:
    try:
        with Image.open(path) as img:
            img.verify()
    except Exception as exc:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail="Arquivo enviado não é uma imagem válida") from exc


@app.post("/foto", status_code=201)
async def enviar_foto(arquivo: UploadFile = File(...)):
    ext = _guess_extension(arquivo)
    if not ext:
        raise HTTPException(status_code=400, detail="Extensão de arquivo não suportada")

    original_name = _sanitize_filename(Path(arquivo.filename or "arquivo").stem)
    saved_name = f"{original_name}_{uuid.uuid4().hex}{ext}"
    destination = BASE_DIR / saved_name

    try:
        with destination.open("wb") as out:
            while True:
                chunk = await arquivo.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
    finally:
        await arquivo.close()

    _validate_image(destination)

    return JSONResponse(status_code=201, content={"arquivo": saved_name})