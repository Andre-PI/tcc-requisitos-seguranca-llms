import os
import uuid
import io
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from PIL import Image

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
    raw_filename = arquivo.filename or ""
    client_ext = Path(raw_filename).suffix.lower()

    if client_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Extensão de arquivo não permitida. Apenas PNG e JPEG são aceitos.",
        )

    upload_dir_env = os.environ.get("TCC_UPLOAD_DIR")
    if not upload_dir_env:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Diretório de upload não configurado.",
        )

    upload_dir = Path(upload_dir_env).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)

    contents = bytearray()
    chunk_size = 64 * 1024

    while True:
        chunk = await arquivo.read(chunk_size)
        if not chunk:
            break
        contents.extend(chunk)
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="O arquivo excede o limite máximo permitido de 2 MiB.",
            )

    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio.",
        )

    try:
        image_stream = io.BytesIO(contents)
        with Image.open(image_stream) as img:
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
                    detail="Dimensões da imagem excedem o limite de 1024x1024 pixels.",
                )

            img.verify()

        # Decodifica completamente para verificar integridade e rejeitar corrupção
        image_stream.seek(0)
        with Image.open(image_stream) as img:
            img.load()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de imagem inválido ou corrompido.",
        )

    target_ext = FORMAT_TO_EXT[img_format]
    unique_filename = f"{uuid.uuid4().hex}{target_ext}"
    destination = (upload_dir / unique_filename).resolve()

    if upload_dir not in destination.parents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Caminho de gravação inválido.",
        )

    try:
        with open(destination, "wb") as f:
            f.write(contents)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao salvar a imagem no servidor.",
        )

    return {"arquivo": unique_filename}