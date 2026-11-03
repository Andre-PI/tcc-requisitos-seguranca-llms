import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from starlette.status import HTTP_201_CREATED
from PIL import Image
from io import BytesIO

TCC_UPLOAD_DIR = os.getenv("TCC_UPLOAD_DIR")
if not TCC_UPLOAD_DIR:
    raise RuntimeError("TCC_UPLOAD_DIR environment variable is not set")

app = FastAPI()

@app.post("/foto", status_code=HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    if not arquivo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Arquivo deve ser uma imagem")

    try:
        contents = await arquivo.read()
        # Verifica se é uma imagem válida
        Image.open(BytesIO(contents)).verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Arquivo inválido ou corrompido")

    nome_salvo = arquivo.filename
    caminho = os.path.join(TCC_UPLOAD_DIR, nome_salvo)

    # Garantir que o diretório existe
    os.makedirs(TCC_UPLOAD_DIR, exist_ok=True)

    # Salva o arquivo
    with open(caminho, "wb") as f:
        f.write(contents)

    return JSONResponse(status_code=HTTP_201_CREATED, content={"arquivo": nome_salvo})