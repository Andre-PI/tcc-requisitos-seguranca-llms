import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(os.environ.get("TCC_ARQUIVOS_DIR", "")).resolve()


@app.get("/download")
async def download_file(nome: str = Query(..., min_length=1)):
    # Normaliza caminhos separando por barras e evita caminhos absolutos no join
    clean_nome = nome.lstrip("/\\")

    target_path = (BASE_DIR / clean_nome).resolve()

    # Prevenção contra Directory Traversal (OWASP)
    try:
        target_path.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    if not target_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    return FileResponse(
        path=target_path,
        media_type="application/octet-stream",
        filename=target_path.name,
    )