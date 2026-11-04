import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()


def _base_dir() -> Path:
    value = os.environ.get("TCC_ARQUIVOS_DIR")
    if not value:
        raise RuntimeError("TCC_ARQUIVOS_DIR nao definido")
    return Path(value)


@app.get("/download")
def download(nome: str = Query(...)) -> FileResponse:
    base = _base_dir()
    path = base / nome

    try:
        resolved_base = base.resolve(strict=True)
        resolved_path = path.resolve(strict=True)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    try:
        resolved_path.relative_to(resolved_base)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    if not resolved_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return FileResponse(
        path=resolved_path,
        status_code=200,
        filename=resolved_path.name,
    )