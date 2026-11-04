import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = os.environ.get("TCC_ARQUIVOS_DIR")
if not BASE_DIR:
    raise RuntimeError("TCC_ARQUIVOS_DIR não definida")

BASE_PATH = Path(BASE_DIR).resolve()


@app.get("/download")
def download(nome: str):
    requested = Path(nome)

    if requested.is_absolute() or any(part == ".." for part in requested.parts):
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido")

    file_path = (BASE_PATH / requested).resolve()

    try:
        file_path.relative_to(BASE_PATH)
    except ValueError:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido")

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(
        path=str(file_path),
        filename=requested.name,
        media_type="application/octet-stream",
    )