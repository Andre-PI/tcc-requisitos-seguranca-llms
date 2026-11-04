import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

_BASE_DIR_RAW = os.environ.get("TCC_ARQUIVOS_DIR")
_BASE_DIR = Path(_BASE_DIR_RAW).resolve(strict=False) if _BASE_DIR_RAW else None


def _safe_resolve_requested_path(nome: str) -> Path:
    if _BASE_DIR is None:
        raise HTTPException(status_code=500, detail="Diretorio base nao configurado")

    if not nome or nome.strip() == "":
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    requested = Path(nome)

    if requested.is_absolute():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    # Reject path traversal and ensure the final path stays within the base dir.
    candidate = (_BASE_DIR / requested).resolve(strict=False)

    try:
        candidate.relative_to(_BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return candidate


@app.get("/download")
def download(nome: str = Query(..., min_length=1)):
    file_path = _safe_resolve_requested_path(nome)

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )