import os
import re
import uuid
import imghdr
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

UPLOAD_DIR = os.environ.get("TCC_UPLOAD_DIR")
if not UPLOAD_DIR:
    raise RuntimeError("TCC_UPLOAD_DIR must be defined before importing this module")

BASE_DIR = Path(UPLOAD_DIR).resolve()
BASE_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
ALLOWED_FORMATS = {"PNG", "JPEG"}


def _sanitize_original_name(name: str) -> str:
    name = Path(name).name
    name = "".join(ch for ch in name if ch not in "\x00\r\n\t")
    name = name.strip()
    if not name:
        return "arquivo"
    return name


def _safe_destination(original_name: str, suffix: str) -> Path:
    original_name = _sanitize_original_name(original_name)
    stem = Path(original_name).stem or "arquivo"
    stem = re.sub(r"[\\/]+", "_", stem)
    stem = stem.strip(" .")
    if not stem:
        stem = "arquivo"
    unique = uuid.uuid4().hex
    filename = f"{stem}_{unique}{suffix}"
    return (BASE_DIR / filename).resolve()


def _ensure_within_base(path: Path) -> None:
    try:
        path.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido")


@app.post("/foto")
async def upload_foto(arquivo: UploadFile = File(...)):
    filename = arquivo.filename or ""
    suffix = Path(filename).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Formato não समर्थado")

    data = await arquivo.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo muito grande")

    kind = imghdr.what(None, h=data)
    if kind not in {"png", "jpeg"}:
        raise HTTPException(status_code=400, detail="Arquivo inválido")

    try:
        image = Image.open(io_bytes := __import__("io").BytesIO(data))
        image.load()
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Arquivo inválido")

    if image.format not in ALLOWED_FORMATS:
        raise HTTPException(status_code=400, detail="Formato não suportado")

    if image.format == "PNG" and suffix not in {".png"}:
        suffix = ".png"
    elif image.format == "JPEG" and suffix not in {".jpg", ".jpeg"}:
        suffix = ".jpg"

    dest = _safe_destination(filename, suffix)
    _ensure_within_base(dest)

    try:
        with open(dest, "xb") as f:
            f.write(data)
    except FileExistsError:
        dest = _safe_destination(filename, suffix)
        _ensure_within_base(dest)
        with open(dest, "xb") as f:
            f.write(data)
    except OSError:
        raise HTTPException(status_code=500, detail="Falha ao salvar arquivo")

    return JSONResponse(status_code=201, content={"arquivo": dest.name})