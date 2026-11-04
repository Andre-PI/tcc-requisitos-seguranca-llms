import os
import uuid
import io
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from PIL import Image, UnidentifiedImageError

app = FastAPI()

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MiB (2097152 bytes)
MAX_WIDTH = 1024
MAX_HEIGHT = 1024
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
ALLOWED_FORMATS = {"PNG", "JPEG"}

FORMAT_TO_EXT = {
    "PNG": ".png",
    "JPEG": ".jpg",
}


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    if not arquivo.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Arquivo inválido.",
        )

    client_ext = Path(arquivo.filename).suffix.lower()
    if client_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Extensão de arquivo não permitida.",
        )

    content = bytearray()
    while True:
        chunk = await arquivo.read(65536)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Tamanho do arquivo excede o limite permitido de 2 MiB.",
            )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio.",
        )

    try:
        buffer = io.BytesIO(content)
        with Image.open(buffer) as img:
            img_format = img.format
            if img_format not in ALLOWED_FORMATS:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Formato de imagem não suportado.",
                )

            width, height = img.size
            if width > MAX_WIDTH or height > MAX_HEIGHT:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Dimensões da imagem ({width}x{height}) excedem o limite de 1024x1024.",
                )

            img.verify()

        buffer.seek(0)
        with Image.open(buffer) as img:
            img.load()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de imagem inválido ou corrompido.",
        )

    upload_dir_env = os.environ.get("TCC_UPLOAD_DIR", ".")
    base_dir = Path(upload_dir_env).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    file_ext = FORMAT_TO_EXT.get(img_format, ".bin")
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    dest_path = (base_dir / unique_filename).resolve()

    if not str(dest_path).startswith(str(base_dir)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Caminho de destino inválido.",
        )

    with open(dest_path, "wb") as f:
        f.write(content)

    return {"arquivo": unique_filename}