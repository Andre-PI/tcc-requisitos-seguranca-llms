import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from PIL import Image
from pathlib import Path

TCC_UPLOAD_DIR = os.environ.get("TCC_UPLOAD_DIR")
if not TCC_UPLOAD_DIR:
    raise RuntimeError("TCC_UPLOAD_DIR environment variable is not set")

upload_path = Path(TCC_UPLOAD_DIR)
upload_path.mkdir(parents=True, exist_ok=True)

app = FastAPI()

@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def enviar_foto(arquivo: UploadFile = File(...)):
    filename = arquivo.filename
    content_type = arquivo.content_type.lower()
    if content_type not in ("image/png", "image/jpeg", "image/jpg"):
        raise HTTPException(status_code=400, detail="Arquivo deve ser PNG ou JPEG")

    try:
        contents = await arquivo.read()
        img = Image.open(BytesIO(contents))
        if img.format not in ("PNG", "JPEG"):
            raise HTTPException(status_code=400, detail="Arquivo deve ser PNG ou JPEG")
    except Exception:
        raise HTTPException(status_code=400, detail="Arquivo inválido ou corrompido")

    ext = ".png" if img.format == "PNG" else ".jpg"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    save_path = upload_path / unique_name
    img.save(save_path)

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": unique_name})

from io import BytesIO