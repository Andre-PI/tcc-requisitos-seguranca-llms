import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR_STR = os.environ.get("TCC_ARQUIVOS_DIR", "")
BASE_DIR = Path(BASE_DIR_STR).resolve()


@app.get("/download")
def download(nome: str = Query(..., min_length=1)):
    nome_norm = nome.strip().lstrip("/\\")
    if not nome_norm:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    try:
        requested_path = BASE_DIR.joinpath(nome_norm)
        resolved_path = requested_path.resolve()
    except (ValueError, RuntimeError):
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    try:
        resolved_path.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    if not resolved_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return FileResponse(
        path=resolved_path,
        media_type="application/octet-stream",
        filename=resolved_path.name,
    )