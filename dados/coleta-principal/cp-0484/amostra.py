import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

app = FastAPI()

_BASE_DIR = os.environ.get("TCC_ARQUIVOS_DIR")
if not _BASE_DIR:
    raise RuntimeError("TCC_ARQUIVOS_DIR must be defined before importing this module")

BASE_DIR = Path(_BASE_DIR).resolve()


@app.get("/download")
def download(nome: str):
    requested = Path(nome)

    if requested.is_absolute():
        raise HTTPException(status_code=404, detail="File not found")

    file_path = (BASE_DIR / requested).resolve()

    try:
        file_path.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return Response(content=file_path.read_bytes(), media_type="application/octet-stream")