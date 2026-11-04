import os
import uuid
import io
from fastapi import FastAPI, File, UploadFile, HTTPException, status
from PIL import Image, UnidentifiedImageError

app = FastAPI()

UPLOAD_DIR = os.environ.get("TCC_UPLOAD_DIR", ".")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_FORMATS = {
    "JPEG": ".jpg",
    "PNG": ".png"
}

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png"
}


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    if not arquivo.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido ou nome ausente."
        )

    if arquivo.content_type and arquivo.content_type.lower() not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de conteúdo não suportado. Apenas JPEG e PNG são permitidos."
        )

    contents = await arquivo.read(MAX_FILE_SIZE + 1)
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Arquivo excede o tamanho máximo permitido de 10MB."
        )

    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado está vazio."
        )

    try:
        image = Image.open(io.BytesIO(contents))
        img_format = image.format
        if img_format not in ALLOWED_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de imagem não suportado. Apenas JPEG e PNG são permitidos."
            )
        image.verify()
    except (UnidentifiedImageError, ValueError, Exception):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado não é uma imagem válida."
        )

    extension = ALLOWED_FORMATS[img_format]
    unique_filename = f"{uuid.uuid4().hex}{extension}"

    destination_path = os.path.abspath(os.path.join(UPLOAD_DIR, unique_filename))
    base_dir = os.path.abspath(UPLOAD_DIR)

    if not destination_path.startswith(base_dir + os.sep) and destination_path != base_dir:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Caminho de arquivo inválido."
        )

    with open(destination_path, "wb") as f:
        f.write(contents)

    return {"arquivo": unique_filename}