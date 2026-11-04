import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR_ENV = os.environ.get("TCC_ARQUIVOS_DIR", "")
BASE_DIR = Path(BASE_DIR_ENV).resolve()


@app.get("/download")
def download(nome: str = Query(...)):
    raw_path = Path(nome)

    if raw_path.is_absolute():
        parts = [p for p in raw_path.parts if p not in (raw_path.root, raw_path.anchor)]
        target_path = BASE_DIR.joinpath(*parts)
    else:
        target_path = BASE_DIR.joinpath(raw_path)

    try:
        resolved_path = target_path.resolve()
    except (OSError, RuntimeError):
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    try:
        resolved_path.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    if not resolved_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return FileResponse(
        path=resolved_path,
        media_type="application/octet-stream",
        filename=resolved_path.name,
    )