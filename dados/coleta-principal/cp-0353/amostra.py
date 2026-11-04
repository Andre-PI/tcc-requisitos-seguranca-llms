import os
import uuid
import io
from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

UPLOAD_DIR = os.environ.get("TCC_UPLOAD_DIR", ".")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    contents = await arquivo.read()

    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio",
        )

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Arquivo excede o tamanho maximo permitido",
        )

    try:
        image = Image.open(io.BytesIO(contents))
        img_format = image.format
        image.verify()
    except (UnidentifiedImageError, Exception):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de imagem invalido ou corrompido",
        )

    if img_format not in ("JPEG", "PNG"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas formatos JPEG e PNG sao suportados",
        )

    ext = ".jpg" if img_format == "JPEG" else ".png"
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    destination_path = os.path.join(UPLOAD_DIR, safe_filename)

    real_upload_dir = os.path.realpath(UPLOAD_DIR)
    real_destination = os.path.realpath(destination_path)
    if not (
        real_destination == real_upload_dir
        or real_destination.startswith(real_upload_dir + os.sep)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Caminho de arquivo invalido",
        )

    with open(destination_path, "wb") as f:
        f.write(contents)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"arquivo": safe_filename},
    )