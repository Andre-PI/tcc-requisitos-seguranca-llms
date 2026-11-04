import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR_ENV = "TCC_ARQUIVOS_DIR"
BASE_DIR = os.environ.get(BASE_DIR_ENV)

if not BASE_DIR:
    raise RuntimeError(f"Variável de ambiente obrigatória ausente: {BASE_DIR_ENV}")

BASE_PATH = Path(BASE_DIR).expanduser().resolve()


def _safe_resolve_requested_path(nome: str) -> Path:
    if nome is None:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    if "\x00" in nome:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    requested = Path(nome)

    if requested.is_absolute():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    target = (BASE_PATH / requested).resolve()

    try:
        target.relative_to(BASE_PATH)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return target


@app.get("/download")
def download(nome: str = Query(..., min_length=1)):
    target = _safe_resolve_requested_path(nome)

    if not target.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(
        path=str(target),
        media_type="application/octet-stream",
        filename=target.name,
    )