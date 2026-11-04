import os
import uuid
import shutil
from fastapi import FastAPI, File, UploadFile, status
from fastapi.responses import JSONResponse

app = FastAPI()


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def enviar_foto(arquivo: UploadFile = File(...)):
    upload_dir = os.environ.get("TCC_UPLOAD_DIR", ".")
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(arquivo.filename or "")[1]
    nome_salvo = f"{uuid.uuid4().hex}{ext}"
    caminho_completo = os.path.join(upload_dir, nome_salvo)

    with open(caminho_completo, "wb") as buffer:
        shutil.copyfileobj(arquivo.file, buffer)

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": nome_salvo})