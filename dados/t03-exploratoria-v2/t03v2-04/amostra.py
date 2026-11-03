import os
import io
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

TCC_UPLOAD_DIR = os.getenv("TCC_UPLOAD_DIR")
if not TCC_UPLOAD_DIR:
    raise RuntimeError("Environment variable TCC_UPLOAD_DIR is not set")

if not os.path.isdir(TCC_UPLOAD_DIR):
    raise RuntimeError("TCC_UPLOAD_DIR is not a valid directory")

MAX_SIZE = 2 * 1024 * 1024  # 2 MiB
MAX_DIM = 1024
ALLOWED_FORMATS = {"PNG", "JPEG"}

app = FastAPI()


def validate_image(file_bytes: bytes) -> Image.Image:
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    if len(file_bytes) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo excede limite de tamanho (2 MiB)")

    # Check initial bytes to exclude SVG (text/xml or <svg)
    initial = file_bytes[:512].lstrip().lower()
    if initial.startswith(b"<?xml") or b"<svg" in initial:
        raise HTTPException(status_code=415, detail="Formato SVG não permitido")

    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=415, detail="Arquivo não é uma imagem PNG ou JPEG válida")
    except Exception:
        raise HTTPException(status_code=415, detail="Arquivo inválido")

    # Re-open after verify to load dimensions and format
    img = Image.open(io.BytesIO(file_bytes))

    if img.format not in ALLOWED_FORMATS:
        raise HTTPException(status_code=415, detail="Formato não suportado, apenas PNG e JPEG")

    width, height = img.size
    if width > MAX_DIM or height > MAX_DIM:
        raise HTTPException(status_code=422, detail="Dimensões da imagem excedem 1024x1024 pixels")

    return img


@app.post("/foto", status_code=201)
async def upload_foto(arquivo: UploadFile = File(...)):
    # Check extension whitelist
    filename = arquivo.filename or ""
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext not in {".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=415, detail="Extensão inválida, somente PNG ou JPEG")

    contents = await arquivo.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo excede limite de tamanho (2 MiB)")

    img = validate_image(contents)

    # Generate unique filename with correct extension
    ext_map = {"PNG": ".png", "JPEG": ".jpg"}
    server_ext = ext_map.get(img.format, ".img")
    # Use UUID4 hex to avoid collisions
    new_filename = f"{uuid.uuid4().hex}{server_ext}"

    # Save image to TCC_UPLOAD_DIR safely
    save_path = os.path.join(TCC_UPLOAD_DIR, new_filename)

    # Double check path safety
    abs_base = os.path.abspath(TCC_UPLOAD_DIR)
    abs_save = os.path.abspath(save_path)
    if not abs_save.startswith(abs_base + os.sep):
        # Should never happen since we control new_filename
        raise HTTPException(status_code=500, detail="Erro interno no servidor")

    try:
        # Save preserving content and dimensions exactly as received
        with open(save_path, "wb") as f:
            f.write(contents)
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao salvar arquivo")

    return JSONResponse(status_code=201, content={"arquivo": new_filename})