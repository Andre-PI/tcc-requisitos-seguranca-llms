import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

_BASE_DIR_STR = os.environ.get("TCC_ARQUIVOS_DIR")
if not _BASE_DIR_STR:
    raise RuntimeError("A variável de ambiente TCC_ARQUIVOS_DIR deve estar definida antes da importação.")

BASE_DIR = Path(_BASE_DIR_STR).expanduser().resolve(strict=False)


def _resolve_safe_path(nome: str) -> Path:
    if nome is None:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    raw = nome.strip()
    if not raw:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    candidate = (BASE_DIR / raw).resolve(strict=False)

    try:
        candidate.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return candidate


@app.get("/download")
def download(nome: str = Query(..., min_length=1)):
    file_path = _resolve_safe_path(nome)

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(
        path=str(file_path),
        status_code=200,
        media_type="application/octet-stream",
        filename=file_path.name,
    )