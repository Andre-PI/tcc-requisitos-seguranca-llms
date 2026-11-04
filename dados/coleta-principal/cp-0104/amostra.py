import os
import uuid
from io import BytesIO
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from PIL import Image

app = FastAPI()


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    upload_dir = os.environ.get("TCC_UPLOAD_DIR", ".")
    os.makedirs(upload_dir, exist_ok=True)

    contents = await arquivo.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio.",
        )

    try:
        image = Image.open(BytesIO(contents))
        img_format = image.format
        if img_format not in ("JPEG", "PNG"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de imagem não suportado. Apenas PNG e JPEG são permitidos.",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de imagem inválido.",
        )

    ext = ".jpg" if img_format == "JPEG" else ".png"

    orig_filename = arquivo.filename or ""
    clean_name = os.path.basename(orig_filename)

    unique_prefix = uuid.uuid4().hex
    if clean_name:
        base, _ = os.path.splitext(clean_name)
        saved_filename = f"{unique_prefix}_{base}{ext}"
    else:
        saved_filename = f"{unique_prefix}{ext}"

    dest_path = os.path.join(upload_dir, saved_filename)
    with open(dest_path, "wb") as f:
        f.write(contents)

    return {"arquivo": saved_filename}