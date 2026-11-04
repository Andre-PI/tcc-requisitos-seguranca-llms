import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

_BASE_DIR_STR = os.environ.get("TCC_ARQUIVOS_DIR")
if not _BASE_DIR_STR:
    raise RuntimeError("TCC_ARQUIVOS_DIR nao definida")

_BASE_DIR = Path(_BASE_DIR_STR).expanduser().resolve(strict=True)


def _resolve_safe_path(nome: str) -> Path:
    if nome is None or nome == "":
        raise HTTPException(status_code=400, detail="Parametro invalido")

    try:
        candidate = (_BASE_DIR / nome).resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        raise HTTPException(status_code=400, detail="Parametro invalido")

    try:
        candidate.relative_to(_BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return candidate


@app.get("/download")
def download(nome: str = Query(...)):
    path = _resolve_safe_path(nome)

    if not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return FileResponse(
        path=path,
        media_type="application/octet-stream",
        filename=path.name,
    )