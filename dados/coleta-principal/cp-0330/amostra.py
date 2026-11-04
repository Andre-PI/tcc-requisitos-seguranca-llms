import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

app = FastAPI()


def _get_base_dir() -> Path:
    base = os.environ.get("TCC_ARQUIVOS_DIR")
    if not base:
        raise RuntimeError("TCC_ARQUIVOS_DIR não definida")
    return Path(base).resolve()


BASE_DIR = _get_base_dir()


def _safe_resolve(nome: str) -> Path:
    if not nome or nome.strip() == "":
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    candidate = (BASE_DIR / nome).resolve()

    try:
        candidate.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return candidate


@app.get("/download")
def download(nome: str = Query(..., min_length=1)) -> Response:
    file_path = _safe_resolve(nome)

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    try:
        content = file_path.read_bytes()
    except OSError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return Response(
        content=content,
        media_type="application/octet-stream",
        status_code=200,
    )