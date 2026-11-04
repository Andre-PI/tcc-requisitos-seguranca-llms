import os
import uuid
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, status
from fastapi.responses import JSONResponse

app = FastAPI()

UPLOAD_DIR = Path(os.environ.get("TCC_UPLOAD_DIR", "."))

@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    ext = Path(arquivo.filename or "").suffix
    nome_salvo = f"{uuid.uuid4()}{ext}"
    caminho_arquivo = UPLOAD_DIR / nome_salvo
    
    with caminho_arquivo.open("wb") as buffer:
        shutil.copyfileobj(arquivo.file, buffer)
        
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": nome_salvo})