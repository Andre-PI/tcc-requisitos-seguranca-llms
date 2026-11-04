import os
import uuid
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, status

app = FastAPI()

UPLOAD_DIR = Path(os.environ.get("TCC_UPLOAD_DIR", "."))


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def enviar_foto(arquivo: UploadFile = File(...)):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    ext = Path(arquivo.filename or "").suffix
    nome_salvo = f"{uuid.uuid4().hex}{ext}"
    destino = UPLOAD_DIR / nome_salvo

    with open(destino, "wb") as buffer:
        shutil.copyfileobj(arquivo.file, buffer)

    return {"arquivo": nome_salvo}