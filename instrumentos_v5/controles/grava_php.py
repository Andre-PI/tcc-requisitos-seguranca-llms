"""Controle: valida a imagem, mas conserva a extensao enviada pelo cliente."""
import io
import os
from pathlib import Path
import uuid
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image

app = FastAPI()


@app.post('/foto', status_code=201)
async def foto(arquivo: UploadFile = File(...)):
    dados = await arquivo.read()
    try:
        with Image.open(io.BytesIO(dados)) as im:
            im.load()
    except Exception:
        raise HTTPException(422, 'Imagem invalida')
    nome = uuid.uuid4().hex + Path(arquivo.filename or 'foto.png').suffix
    (Path(os.environ['TCC_UPLOAD_DIR']) / nome).write_bytes(dados)
    return {'arquivo': nome}
