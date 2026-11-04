import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = os.environ.get("TCC_ARQUIVOS_DIR")
if not BASE_DIR:
    raise RuntimeError("TCC_ARQUIVOS_DIR nao definida")

BASE_PATH = Path(BASE_DIR).resolve()


@app.get("/download")
def download(nome: str):
    requested = Path(nome)

    if requested.is_absolute():
        raise HTTPException(status_code=400, detail="Caminho invalido")

    target = (BASE_PATH / requested).resolve()

    try:
        target.relative_to(BASE_PATH)
    except ValueError:
        raise HTTPException(status_code=403, detail="Acesso negado")

    if not target.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return FileResponse(path=str(target), filename=target.name)