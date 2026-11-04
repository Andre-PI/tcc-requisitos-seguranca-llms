import os
import uuid
from io import BytesIO
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from PIL import Image, ImageOps

app = FastAPI()

UPLOAD_DIR = os.environ.get("TCC_UPLOAD_DIR", "/tmp")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    contents = bytearray()
    while chunk := await arquivo.read(1024 * 1024):
        contents.extend(chunk)
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Arquivo excede o tamanho máximo permitido.",
            )

    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio.",
        )

    try:
        buffer = BytesIO(contents)
        with Image.open(buffer) as img:
            img_format = img.format
            if img_format not in ("JPEG", "PNG"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato de imagem não suportado. Apenas JPEG e PNG são aceitos.",
                )

            img = ImageOps.exif_transpose(img)

            extension = ".jpg" if img_format == "JPEG" else ".png"
            filename = f"{uuid.uuid4().hex}{extension}"

            os.makedirs(UPLOAD_DIR, exist_ok=True)
            target_path = os.path.join(UPLOAD_DIR, filename)

            if img_format == "JPEG":
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                img.save(target_path, format="JPEG", quality=95)
            else:
                img.save(target_path, format="PNG")

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de imagem inválido ou corrompido.",
        )

    return {"arquivo": filename}