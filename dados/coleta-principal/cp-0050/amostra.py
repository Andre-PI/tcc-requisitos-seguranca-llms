import os
import uuid
import io
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from PIL import Image, UnidentifiedImageError

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MiB
MAX_WIDTH = 1024
MAX_HEIGHT = 1024

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
ALLOWED_FORMATS = {"PNG": ".png", "JPEG": ".jpg"}

app = FastAPI()


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    upload_dir_env = os.environ.get("TCC_UPLOAD_DIR")
    if not upload_dir_env:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Diretório de upload não configurado.",
        )

    base_dir = Path(upload_dir_env).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    filename = arquivo.filename or ""
    client_ext = Path(filename).suffix.lower()

    if client_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Tipo de arquivo não permitido. Apenas PNG e JPEG são aceitos.",
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

    try:
        image_stream = io.BytesIO(content)
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
                    detail="Dimensões da imagem excedem o limite permitido de 1024x1024 pixels.",
                )

            img.verify()

        image_stream.seek(0)
        with Image.open(image_stream) as img:
            img.load()

    except (UnidentifiedImageError, SyntaxError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo corrompido ou imagem inválida.",
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível processar a imagem enviada.",
        )

    extension = ALLOWED_FORMATS[img_format]
    unique_name = f"{uuid.uuid4().hex}{extension}"
    target_path = (base_dir / unique_name).resolve()

    if target_path.parent != base_dir:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tentativa inválida de caminho de destino.",
        )

    with open(target_path, "wb") as f:
        f.write(content)

    return {"arquivo": unique_name}