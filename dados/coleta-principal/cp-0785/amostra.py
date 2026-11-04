import os
import uuid
from io import BytesIO
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, status
from PIL import Image

app = FastAPI()

UPLOAD_DIR = os.environ.get("TCC_UPLOAD_DIR", ".")


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile):
    contents = await arquivo.read()

    try:
        img = Image.open(BytesIO(contents))
        img.verify()
        formato = img.format
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido ou corrompido.",
        )

    if formato not in ("PNG", "JPEG"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de imagem não suportado. Apenas PNG e JPEG são permitidos.",
        )

    ext = ".png" if formato == "PNG" else ".jpg"

    original_filename = Path(arquivo.filename or "upload").name
    safe_name = original_filename.replace("/", "_").replace("\\", "_")
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"

    if not unique_name.lower().endswith(ext):
        unique_name = f"{unique_name}{ext}"

    dest_dir = Path(UPLOAD_DIR)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / unique_name

    with open(dest_path, "wb") as f:
        f.write(contents)

    return {"arquivo": unique_name}