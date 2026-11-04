import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

app = FastAPI()


def _base_dir() -> Path:
    base = os.environ.get("TCC_ARQUIVOS_DIR")
    if not base:
        raise RuntimeError("TCC_ARQUIVOS_DIR nao definida")
    return Path(base).expanduser().resolve(strict=True)


BASE_DIR = _base_dir()


def _safe_resolve(nome: str) -> Path:
    if nome is None or nome == "":
        raise HTTPException(status_code=400, detail="Parametro 'nome' invalido")

    candidate = Path(nome)

    if candidate.is_absolute():
        raise HTTPException(status_code=400, detail="Parametro 'nome' invalido")

    resolved = (BASE_DIR / candidate).resolve(strict=False)

    try:
        resolved.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return resolved


@app.get("/download")
def download(nome: str = Query(...)):
    path = _safe_resolve(nome)

    if not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    try:
        content = path.read_bytes()
    except OSError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return Response(
        content=content,
        media_type="application/octet-stream",
        status_code=200,
    )