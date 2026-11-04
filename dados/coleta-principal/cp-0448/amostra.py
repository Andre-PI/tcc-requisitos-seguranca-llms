import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR_ENV = os.environ.get("TCC_ARQUIVOS_DIR", "")
BASE_DIR = Path(BASE_DIR_ENV).resolve()


@app.get("/download")
def download_arquivo(nome: str = Query(...)):
    if not nome or "\x00" in nome:
        raise HTTPException(status_code=400, detail="Nome de arquivo invalido.")

    rel_path = Path(nome)
    if rel_path.is_absolute():
        rel_path = Path(*rel_path.parts[1:])

    resolved_path = (BASE_DIR / rel_path).resolve()

    try:
        resolved_path.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=400, detail="Acesso negado.")

    if resolved_path == BASE_DIR or not resolved_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado.")

    return FileResponse(path=resolved_path, media_type="application/octet-stream")