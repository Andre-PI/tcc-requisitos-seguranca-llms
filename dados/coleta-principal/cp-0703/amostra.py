import os
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

UPLOAD_DIR = os.environ.get("TCC_UPLOAD_DIR", ".")


@app.post("/foto", status_code=201)
async def upload_foto(arquivo: UploadFile = File(...)):
    if not arquivo.filename:
        raise HTTPException(status_code=400, detail="Arquivo inválido")

    _, ext = os.path.splitext(arquivo.filename)
    nome_salvo = f"{uuid.uuid4()}{ext}"
    caminho_completo = os.path.join(UPLOAD_DIR, nome_salvo)

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    try:
        with open(caminho_completo, "wb") as buffer:
            shutil.copyfileobj(arquivo.file, buffer)
    finally:
        await arquivo.close()

    return JSONResponse(status_code=201, content={"arquivo": nome_salvo})