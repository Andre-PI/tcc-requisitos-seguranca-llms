import os
import uuid
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, status

app = FastAPI()

UPLOAD_DIR = Path(os.environ.get("TCC_UPLOAD_DIR", "."))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def enviar_foto(arquivo: UploadFile = File(...)):
    extensao = Path(arquivo.filename or "").suffix
    nome_salvo = f"{uuid.uuid4()}{extensao}"
    destino = UPLOAD_DIR / nome_salvo

    try:
        with destino.open("wb") as buffer:
            shutil.copyfileobj(arquivo.file, buffer)
    finally:
        await arquivo.close()

    return {"arquivo": nome_salvo}