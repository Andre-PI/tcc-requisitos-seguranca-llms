import os
import uuid
from io import BytesIO
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from PIL import Image

app = FastAPI()

UPLOAD_DIR = os.getenv("TCC_UPLOAD_DIR", ".")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    contents = await arquivo.read()

    try:
        with Image.open(BytesIO(contents)) as img:
            img_format = img.format
            if img_format not in ("JPEG", "PNG"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato de imagem não suportado. Apenas PNG e JPEG são permitidos.",
                )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido ou não suportado.",
        )

    orig_name = arquivo.filename or ""
    _, ext = os.path.splitext(orig_name)

    if not ext:
        ext = ".png" if img_format == "PNG" else ".jpg"

    safe_prefix = str(uuid.uuid4())
    if orig_name:
        filename = f"{safe_prefix}_{orig_name}"
    else:
        filename = f"{safe_prefix}{ext}"

    dest_path = os.path.join(UPLOAD_DIR, filename)

    with open(dest_path, "wb") as f:
        f.write(contents)

    return {"arquivo": filename}