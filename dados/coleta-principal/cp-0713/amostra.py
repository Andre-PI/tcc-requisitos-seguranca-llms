import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

_BASE_DIR_RAW = os.environ.get("TCC_ARQUIVOS_DIR")
if not _BASE_DIR_RAW:
    raise RuntimeError("TCC_ARQUIVOS_DIR nao definida")

_BASE_DIR = Path(_BASE_DIR_RAW).resolve(strict=True)


def _safe_resolve(nome: str) -> Path:
    if nome is None:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    nome = nome.strip()
    if not nome:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    if "\x00" in nome:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    candidate = (_BASE_DIR / nome).resolve(strict=False)

    try:
        candidate.relative_to(_BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return candidate


@app.get("/download")
def download(nome: str = Query(..., min_length=1)):
    file_path = _safe_resolve(nome)
    return FileResponse(
        path=file_path,
        status_code=200,
        media_type="application/octet-stream",
        filename=file_path.name,
    )