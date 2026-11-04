import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = os.environ.get("TCC_ARQUIVOS_DIR")
if not BASE_DIR:
    raise RuntimeError("Variável de ambiente TCC_ARQUIVOS_DIR não definida")

BASE_PATH = Path(BASE_DIR).resolve()


@app.get("/download")
def download(nome: str = Query(...)):
    requested_path = (BASE_PATH / nome).resolve()

    try:
        requested_path.relative_to(BASE_PATH)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    if not requested_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(
        path=str(requested_path),
        media_type="application/octet-stream",
        filename=requested_path.name,
    )