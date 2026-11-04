import os
import uuid
import io
from PIL import Image, ImageOps
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

app = FastAPI()

UPLOAD_DIR = os.getenv("TCC_UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_FORMATS = {"JPEG": ".jpg", "PNG": ".png"}


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    content = await arquivo.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Arquivo excede o tamanho maximo permitido.",
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio.",
        )

    try:
        image = Image.open(io.BytesIO(content))
        image.verify()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo invalido ou corrompido.",
        )

    image_format = image.format
    if image_format not in ALLOWED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de imagem nao suportado. Use PNG ou JPEG.",
        )

    # Reabre a imagem para processamento e remocao de metadados potencialmente maliciosos
    try:
        image = Image.open(io.BytesIO(content))
        image = ImageOps.exif_transpose(image)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Falha ao processar a imagem.",
        )

    ext = ALLOWED_FORMATS[image_format]
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    output_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        if image_format == "JPEG":
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            image.save(output_path, format="JPEG", quality=95)
        elif image_format == "PNG":
            image.save(output_path, format="PNG")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao salvar a imagem.",
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"arquivo": unique_filename},
    )