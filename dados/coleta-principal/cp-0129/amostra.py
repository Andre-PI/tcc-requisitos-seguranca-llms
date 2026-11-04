import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

app = FastAPI()

_BASE_DIR_RAW = os.environ.get("TCC_ARQUIVOS_DIR")
if not _BASE_DIR_RAW:
    raise RuntimeError("TCC_ARQUIVOS_DIR não definida")

_BASE_DIR = Path(_BASE_DIR_RAW).expanduser().resolve(strict=True)


def _safe_resolve(user_name: str) -> Path:
    if user_name is None or user_name == "":
        raise HTTPException(status_code=400, detail="Parâmetro 'nome' inválido")

    candidate = Path(user_name)

    if candidate.is_absolute():
        raise HTTPException(status_code=400, detail="Parâmetro 'nome' inválido")

    # Reject traversal attempts early
    if any(part == ".." for part in candidate.parts):
        raise HTTPException(status_code=400, detail="Parâmetro 'nome' inválido")

    # Resolve against base and ensure containment
    resolved = (_BASE_DIR / candidate).resolve(strict=False)

    try:
        resolved.relative_to(_BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=400, detail="Parâmetro 'nome' inválido")

    return resolved


@app.get("/download")
def download(nome: str = Query(...)):
    path = _safe_resolve(nome)

    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    try:
        content = path.read_bytes()
    except OSError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return Response(content=content, media_type="application/octet-stream")