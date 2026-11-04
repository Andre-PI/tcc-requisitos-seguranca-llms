import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR_ENV = os.environ.get("TCC_ARQUIVOS_DIR", "")
BASE_DIR = Path(BASE_DIR_ENV).resolve()


@app.get("/download")
def download_arquivo(nome: str = Query(..., min_length=1)):
    if not BASE_DIR_ENV:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo não encontrado",
        )

    nome_sanitizado = nome.lstrip("/\\")

    caminho_solicitado = (BASE_DIR / nome_sanitizado).resolve()

    try:
        caminho_solicitado.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo não encontrado",
        )

    if not caminho_solicitado.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo não encontrado",
        )

    return FileResponse(
        path=caminho_solicitado,
        media_type="application/octet-stream",
        filename=caminho_solicitado.name,
    )