import os
import uuid
from io import BytesIO
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, status
from PIL import Image

app = FastAPI()

UPLOAD_DIR = Path(os.environ.get("TCC_UPLOAD_DIR", "."))
ALLOWED_FORMATS = {"PNG": ".png", "JPEG": ".jpg"}


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile):
    contents = await arquivo.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio.",
        )

    try:
        image = Image.open(BytesIO(contents))
        img_format = image.format
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de imagem inválido.",
        )

    if img_format not in ALLOWED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato não suportado. Apenas PNG e JPEG são permitidos.",
        )

    original_filename = arquivo.filename or "imagem"
    base_stem = Path(original_filename).stem
    ext = ALLOWED_FORMATS[img_format]
    unique_id = uuid.uuid4().hex
    saved_filename = f"{base_stem}_{unique_id}{ext}"

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    destination = UPLOAD_DIR / saved_filename

    with open(destination, "wb") as f:
        f.write(contents)

    return {"arquivo": saved_filename}