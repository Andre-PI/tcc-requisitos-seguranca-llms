import os
from pathlib import Path
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

app = FastAPI()


def _get_base_dir() -> Path:
    base = os.environ.get("TCC_ARQUIVOS_DIR")
    if not base:
        raise RuntimeError("TCC_ARQUIVOS_DIR não definida")
    return Path(base).resolve()


BASE_DIR = _get_base_dir()


@app.get("/download")
def download(nome: str = Query(...)) -> Response:
    rel_name = unquote(nome)
    target = (BASE_DIR / rel_name).resolve()

    try:
        target.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    if not target.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return Response(
        content=target.read_bytes(),
        media_type="application/octet-stream",
        status_code=200,
    )