import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(os.environ.get("TCC_ARQUIVOS_DIR", "")).resolve()


@app.get("/download")
async def download_arquivo(nome: str = Query(...)):
    arquivo_path = (BASE_DIR / nome).resolve()

    if not arquivo_path.is_relative_to(BASE_DIR):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    if not arquivo_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(
        path=arquivo_path,
        media_type="application/octet-stream",
        filename=arquivo_path.name,
    )