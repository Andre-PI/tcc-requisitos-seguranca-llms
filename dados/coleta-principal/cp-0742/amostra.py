import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

app = FastAPI()

_BASE_DIR_RAW = os.environ.get("TCC_ARQUIVOS_DIR")
if not _BASE_DIR_RAW:
    raise RuntimeError("TCC_ARQUIVOS_DIR nao definido")

_BASE_DIR = Path(_BASE_DIR_RAW).expanduser().resolve(strict=True)


def _safe_resolve_requested_path(nome: str) -> Path:
    if nome is None or nome == "":
        raise HTTPException(status_code=400, detail="nome invalido")

    requested = Path(nome)

    if requested.is_absolute():
        raise HTTPException(status_code=400, detail="nome invalido")

    try:
        candidate = (_BASE_DIR / requested).resolve(strict=True)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="arquivo nao encontrado")
    except OSError:
        raise HTTPException(status_code=400, detail="nome invalido")

    try:
        candidate.relative_to(_BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="arquivo nao encontrado")

    return candidate


@app.get("/download")
def download(nome: str = Query(...)):
    file_path = _safe_resolve_requested_path(nome)
    try:
        data = file_path.read_bytes()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="arquivo nao encontrado")
    except OSError:
        raise HTTPException(status_code=404, detail="arquivo nao encontrado")

    return Response(content=data, media_type="application/octet-stream", status_code=200)