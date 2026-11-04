import os
import uuid
from io import BytesIO
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from PIL import Image, ImageOps

app = FastAPI()

UPLOAD_DIR = os.environ.get("TCC_UPLOAD_DIR", "/tmp")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    contents = await arquivo.read()

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Arquivo excede o tamanho maximo permitido.",
        )

    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio.",
        )

    try:
        image_stream = BytesIO(contents)
        with Image.open(image_stream) as img:
            img.verify()

        image_stream.seek(0)
        with Image.open(image_stream) as img:
            image_format = img.format
            if image_format not in ("JPEG", "PNG"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato de imagem nao suportado. Use PNG ou JPEG.",
                )

            ext = ".jpg" if image_format == "JPEG" else ".png"
            filename = f"{uuid.uuid4().hex}{ext}"

            os.makedirs(UPLOAD_DIR, exist_ok=True)
            file_path = os.path.join(UPLOAD_DIR, filename)

            img = ImageOps.exif_transpose(img)

            if image_format == "JPEG":
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(file_path, format="JPEG", quality=95)
            else:
                img.save(file_path, format="PNG")

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de imagem invalido ou corrompido.",
        )
    finally:
        await arquivo.close()

    return {"arquivo": filename}