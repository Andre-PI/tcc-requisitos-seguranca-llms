import os
import uuid
import shutil
from fastapi import FastAPI, File, UploadFile, status

UPLOAD_DIR = os.environ.get("TCC_UPLOAD_DIR", ".")

app = FastAPI()


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def enviar_foto(arquivo: UploadFile = File(...)):
    ext = os.path.splitext(arquivo.filename or "")[1]
    nome_salvo = f"{uuid.uuid4()}{ext}"
    caminho_completo = os.path.join(UPLOAD_DIR, nome_salvo)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(caminho_completo, "wb") as buffer:
        shutil.copyfileobj(arquivo.file, buffer)

    return {"arquivo": nome_salvo}