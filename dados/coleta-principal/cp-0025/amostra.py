import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

app = FastAPI()

BASE_DIR = os.environ.get("TCC_ARQUIVOS_DIR")
BASE_PATH = Path(BASE_DIR).resolve() if BASE_DIR else None


@app.get("/download")
def download(nome: str):
    if BASE_PATH is None:
        raise HTTPException(status_code=500, detail="TCC_ARQUIVOS_DIR nao definido")

    requested = Path(nome)

    if requested.is_absolute():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    file_path = (BASE_PATH / requested).resolve()

    try:
        file_path.relative_to(BASE_PATH)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    content = file_path.read_bytes()
    return Response(content=content, media_type="application/octet-stream", status_code=200)