import os
import re
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from PIL import Image
from starlette.datastructures import UploadFile as StarletteUploadFile

app = FastAPI()

UPLOAD_DIR = os.getenv("TCC_UPLOAD_DIR")
if not UPLOAD_DIR:
    raise RuntimeError("TCC_UPLOAD_DIR environment variable is not set")
if not os.path.isdir(UPLOAD_DIR):
    raise RuntimeError(f"TCC_UPLOAD_DIR path does not exist or is not a directory: {UPLOAD_DIR}")

ALLOWED_MIME_TYPES = {"image/png", "image/jpeg"}
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}

_filename_sanitize_regex = re.compile(r"[^A-Za-z0-9_.-]+", re.UNICODE)


def sanitize_filename(filename: str) -> str:
    # Normalize filename: remove path components, keep unicode chars, replace spaces with _
    filename = os.path.basename(filename)
    filename = filename.strip().replace(" ", "_")
    # Remove characters not allowed, preserving unicode letters/numbers and _ . -
    filename = _filename_sanitize_regex.sub("", filename)
    if not filename:
        filename = "file"
    return filename


def validate_image_format(file: StarletteUploadFile) -> str:
    # Read enough bytes to identify image format without loading entire file into memory
    try:
        file.file.seek(0)
        image = Image.open(file.file)
        image.verify()  # verify image integrity, does not load entire image
        file.file.seek(0)
    except Exception:
        raise HTTPException(status_code=400, detail="Arquivo não é uma imagem PNG ou JPEG válida")

    fmt = image.format
    if fmt not in ("PNG", "JPEG"):
        raise HTTPException(status_code=400, detail="Formato de imagem não suportado (somente PNG e JPEG)")
    return fmt


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    if arquivo.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Content-Type não permitido. Somente image/png e image/jpeg")

    fmt = validate_image_format(arquivo)

    original_name = sanitize_filename(arquivo.filename)
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        # Force extension by format detected
        ext = ".png" if fmt == "PNG" else ".jpg"

    unique_id = uuid.uuid4().hex
    saved_filename = f"{unique_id}{ext}"
    saved_path = os.path.join(UPLOAD_DIR, saved_filename)

    try:
        # Reopen image to preserve visual content and dimensions, save it as is
        arquivo.file.seek(0)
        image = Image.open(arquivo.file)
        image.save(saved_path, format=fmt)
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao salvar a imagem")

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": saved_filename})