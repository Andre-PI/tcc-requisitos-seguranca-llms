import io
import os
import uuid
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MiB
MAX_WIDTH = 1024
MAX_HEIGHT = 1024
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
ALLOWED_FORMATS = {"PNG": ".png", "JPEG": ".jpg"}

app = FastAPI()


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    raw_filename = arquivo.filename or ""
    client_ext = Path(raw_filename).suffix.lower()

    if client_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Tipo de arquivo ou extensão não suportada.",
        )

    content = bytearray()
    chunk_size = 64 * 1024

    while True:
        chunk = await arquivo.read(chunk_size)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="O arquivo excede o limite máximo permitido de 2 MiB.",
            )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio.",
        )

    image_stream = io.BytesIO(content)
    try:
        with Image.open(image_stream) as img:
            img_format = img.format
            if img_format not in ALLOWED_FORMATS:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Formato de imagem inválido.",
                )

            width, height = img.size
            if width > MAX_WIDTH or height > MAX_HEIGHT:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Dimensões da imagem excedem o limite de 1024x1024 pixels.",
                )

            img.verify()

        # Decodificar e carregar pixels completamente para garantir integridade
        image_stream.seek(0)
        with Image.open(image_stream) as img:
            img.load()

    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Exception):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de imagem inválido ou corrompido.",
        )

    upload_dir_env = os.environ.get("TCC_UPLOAD_DIR", ".")
    base_dir = Path(upload_dir_env).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    extension = ALLOWED_FORMATS[img_format]
    if client_ext in {".jpg", ".jpeg"} and img_format == "JPEG":
        extension = client_ext

    saved_filename = f"{uuid.uuid4().hex}{extension}"
    target_path = (base_dir / saved_filename).resolve()

    if target_path.parent != base_dir:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Caminho de gravação inválido.",
        )

    while target_path.exists():
        saved_filename = f"{uuid.uuid4().hex}{extension}"
        target_path = (base_dir / saved_filename).resolve()

    target_path.write_bytes(content)

    return {"arquivo": saved_filename}