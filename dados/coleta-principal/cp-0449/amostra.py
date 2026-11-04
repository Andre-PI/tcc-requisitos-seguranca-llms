import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse

app = FastAPI()

_BASE_DIR_RAW = os.environ.get("TCC_ARQUIVOS_DIR")
if not _BASE_DIR_RAW:
    raise RuntimeError("TCC_ARQUIVOS_DIR must be defined before importing this module")

BASE_DIR = Path(_BASE_DIR_RAW).resolve()


def _safe_resolve_requested_path(nome: str) -> Path:
    if not nome or nome.strip() == "":
        raise HTTPException(status_code=404, detail="File not found")

    requested = Path(nome)

    # Reject absolute paths and any attempt to traverse outside the base directory.
    if requested.is_absolute():
        raise HTTPException(status_code=404, detail="File not found")

    resolved = (BASE_DIR / requested).resolve()

    try:
        resolved.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="File not found")

    return resolved


@app.get("/download")
def download(nome: str = Query(..., min_length=1)):
    file_path = _safe_resolve_requested_path(nome)

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_handle = open(file_path, "rb")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except OSError:
        raise HTTPException(status_code=404, detail="File not found")

    headers = {
        "Content-Disposition": f'attachment; filename="{file_path.name}"'
    }
    return StreamingResponse(file_handle, media_type="application/octet-stream", headers=headers)