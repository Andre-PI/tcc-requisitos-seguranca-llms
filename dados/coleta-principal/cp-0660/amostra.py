import os
import uuid
import shutil
from fastapi import FastAPI, File, UploadFile, status

app = FastAPI()

UPLOAD_DIR = os.getenv("TCC_UPLOAD_DIR", ".")


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(arquivo.filename or "")[1]
    nome_salvo = f"{uuid.uuid4().hex}{ext}"
    caminho_completo = os.path.join(UPLOAD_DIR, nome_salvo)

    with open(caminho_completo, "wb") as buffer:
        shutil.copyfileobj(arquivo.file, buffer)

    return {"arquivo": nome_salvo}