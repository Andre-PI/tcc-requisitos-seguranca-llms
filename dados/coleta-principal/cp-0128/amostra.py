import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(os.environ.get("TCC_ARQUIVOS_DIR", "")).resolve()


@app.get("/download")
async def download_file(nome: str = Query(...)):
    target_path = (BASE_DIR / nome).resolve()

    try:
        target_path.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404)

    if not target_path.is_file():
        raise HTTPException(status_code=404)

    return FileResponse(path=target_path, media_type="application/octet-stream")