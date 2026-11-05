"""Controle: aceita qualquer nome enviado, mas grava com extensao de imagem gerada no servidor."""
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
            formato = im.format
    except Exception:
        raise HTTPException(422, 'Imagem invalida')
    if formato not in ('PNG', 'JPEG'):
        raise HTTPException(422, 'Imagem invalida')
    nome = uuid.uuid4().hex + ('.png' if formato == 'PNG' else '.jpg')
    (Path(os.environ['TCC_UPLOAD_DIR']) / nome).write_bytes(dados)
    return {'arquivo': nome}
