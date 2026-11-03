import os
from pathlib import Path, PurePosixPath

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

app = FastAPI()

_BASE_DIR = os.environ.get("TCC_ARQUIVOS_DIR")
if not _BASE_DIR:
    raise RuntimeError("A variável de ambiente TCC_ARQUIVOS_DIR deve estar definida antes da importação.")
BASE_DIR = Path(_BASE_DIR).resolve()


def _resolve_path(nome: str) -> Path:
    rel = PurePosixPath(nome)
    if rel.is_absolute() or ".." in rel.parts:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    candidate = (BASE_DIR / Path(*rel.parts)).resolve()
    try:
        candidate.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return candidate


@app.get("/download")
def download(nome: str = Query(...)):
    path = _resolve_path(nome)
    return Response(content=path.read_bytes(), media_type="application/octet-stream", status_code=200)