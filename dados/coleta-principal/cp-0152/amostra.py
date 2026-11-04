import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(os.environ.get("TCC_ARQUIVOS_DIR", "")).resolve()


@app.get("/download")
async def download_arquivo(nome: str = Query(...)):
    relative_path = Path(nome)

    if relative_path.is_absolute():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    try:
        resolved_path = (BASE_DIR / relative_path).resolve()
    except Exception:
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