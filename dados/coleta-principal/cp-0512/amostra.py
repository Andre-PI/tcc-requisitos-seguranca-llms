import io
import os
import uuid
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from PIL import Image, ImageOps

UPLOAD_DIR = Path(os.environ.get("TCC_UPLOAD_DIR", ".")).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

app = FastAPI()


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    contents = await arquivo.read()

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
        with Image.open(io.BytesIO(contents)) as img:
            img_format = img.format
            if img_format not in ("JPEG", "PNG"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato de imagem inválido. Suportados apenas JPEG e PNG.",
                )

            img = ImageOps.exif_transpose(img)

            if img_format == "JPEG":
                ext = ".jpg"
                save_format = "JPEG"
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
            else:
                ext = ".png"
                save_format = "PNG"

            filename = f"{uuid.uuid4().hex}{ext}"
            file_path = (UPLOAD_DIR / filename).resolve()

            if not str(file_path).startswith(str(UPLOAD_DIR)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Caminho de arquivo inválido.",
                )

            img.save(file_path, format=save_format)

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível processar a imagem fornecida.",
        )

    return {"arquivo": filename}