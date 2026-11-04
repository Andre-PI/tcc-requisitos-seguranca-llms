import io
import os
import uuid
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError

app = FastAPI()

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MiB
MAX_WIDTH = 1024
MAX_HEIGHT = 1024

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
FORMAT_EXTENSIONS = {
    "PNG": ".png",
    "JPEG": ".jpg",
}


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    upload_dir_env = os.environ.get("TCC_UPLOAD_DIR")
    if not upload_dir_env:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Diretório de upload não configurado.",
        )

    upload_dir = Path(upload_dir_env).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = arquivo.filename or ""
    client_ext = Path(filename).suffix.lower()
    if client_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Extensão de arquivo não permitida.",
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
                detail="O arquivo excede o limite máximo de 2 MiB.",
            )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado está vazio.",
        )

    try:
        with Image.open(io.BytesIO(content)) as img:
            fmt = img.format
            if fmt not in FORMAT_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Formato de imagem não suportado.",
                )

            width, height = img.size
            if width > MAX_WIDTH or height > MAX_HEIGHT or width <= 0 or height <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="As dimensões da imagem excedem o limite de 1024x1024.",
                )

            img.verify()

        with Image.open(io.BytesIO(content)) as img:
            img.load()

    except (UnidentifiedImageError, SyntaxError):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Arquivo corrompido ou formato não suportado.",
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Falha ao decodificar a imagem enviada.",
        )

    ext = FORMAT_EXTENSIONS[fmt]
    saved_filename = f"{uuid.uuid4().hex}{ext}"
    destination = (upload_dir / saved_filename).resolve()

    if upload_dir not in destination.parents and destination.parent != upload_dir:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Caminho de destino inválido.",
        )

    with open(destination, "wb") as f:
        f.write(content)

    return {"arquivo": saved_filename}