import os
import uuid
from io import BytesIO
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from PIL import Image

app = FastAPI()


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    content = await arquivo.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio."
        )

    try:
        image = Image.open(BytesIO(content))
        image_format = image.format
        if image_format not in ("JPEG", "PNG"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de imagem não suportado. Apenas JPEG e PNG são permitidos.",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de imagem inválido.",
        )

    ext = ".jpg" if image_format == "JPEG" else ".png"

    if arquivo.filename:
        original_name = os.path.basename(arquivo.filename)
        base, _ = os.path.splitext(original_name)
        if base:
            filename = f"{uuid.uuid4().hex}_{base}{ext}"
        else:
            filename = f"{uuid.uuid4().hex}{ext}"
    else:
        filename = f"{uuid.uuid4().hex}{ext}"

    upload_dir = os.environ.get("TCC_UPLOAD_DIR", ".")
    os.makedirs(upload_dir, exist_ok=True)

    dest_path = os.path.join(upload_dir, filename)
    with open(dest_path, "wb") as f:
        f.write(content)

    return {"arquivo": filename}