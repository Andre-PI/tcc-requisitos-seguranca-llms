from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path
import os

app = FastAPI()

BASE_DIR = Path(os.environ.get("TCC_ARQUIVOS_DIR", "")).resolve()


def _safe_resolve(nome: str) -> Path:
    candidate = (BASE_DIR / nome).resolve()
    try:
        candidate.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")
    return candidate


@app.get("/download")
def download(nome: str = Query(...)):
    arquivo = _safe_resolve(nome)
    if not arquivo.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")
    return FileResponse(path=arquivo, filename=arquivo.name, media_type="application/octet-stream")