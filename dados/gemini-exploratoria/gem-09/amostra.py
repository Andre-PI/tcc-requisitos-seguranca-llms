import os
import uuid
import shutil
from fastapi import FastAPI, File, UploadFile, status

UPLOAD_DIR = os.environ.get("TCC_UPLOAD_DIR", "/tmp")

app = FastAPI()


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(arquivo.filename or "")[1]
    nome_salvo = f"{uuid.uuid4().hex}{ext}"
    caminho_arquivo = os.path.join(UPLOAD_DIR, nome_salvo)

    with open(caminho_arquivo, "wb") as buffer:
        shutil.copyfileobj(arquivo.file, buffer)

    return {"arquivo": nome_salvo}