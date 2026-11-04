from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path
import os

app = FastAPI()

BASE_DIR = Path(os.environ.get("TCC_ARQUIVOS_DIR", "")).resolve()


def _safe_resolve(nome: str) -> Path:
    if not nome:
        raise HTTPException(status_code=400, detail="Parâmetro 'nome' é obrigatório.")

    requested = (BASE_DIR / nome).resolve()

    try:
        requested.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    if not requested.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    return requested


@app.get("/download")
def download(nome: str = Query(...)):
    file_path = _safe_resolve(nome)
    return FileResponse(path=file_path, filename=file_path.name, media_type="application/octet-stream")