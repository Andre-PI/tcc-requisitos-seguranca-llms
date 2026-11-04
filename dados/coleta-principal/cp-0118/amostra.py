import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(os.environ.get("TCC_ARQUIVOS_DIR", ".")).resolve()


@app.get("/download")
def download(nome: str = Query(...)):
    raw_path = Path(nome)
    if raw_path.is_absolute():
        raise HTTPException(status_code=400, detail="Invalid file path")

    try:
        target_path = (BASE_DIR / raw_path).resolve()
    except (ValueError, RuntimeError):
        raise HTTPException(status_code=400, detail="Invalid file path")

    if target_path != BASE_DIR and BASE_DIR not in target_path.parents:
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not target_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=target_path,
        media_type="application/octet-stream",
        filename=target_path.name,
    )