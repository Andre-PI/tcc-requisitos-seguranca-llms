import os
import uuid
import shutil
from fastapi import FastAPI, File, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image

app = FastAPI()

UPLOAD_DIR = os.environ.get("TCC_UPLOAD_DIR", ".")


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    ext = os.path.splitext(arquivo.filename or "")[1].lower()
    if not ext:
        ext = ".jpg"

    nome_salvo = f"{uuid.uuid4().hex}{ext}"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    caminho_completo = os.path.join(UPLOAD_DIR, nome_salvo)

    with open(caminho_completo, "wb") as buffer:
        shutil.copyfileobj(arquivo.file, buffer)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"arquivo": nome_salvo},
    )