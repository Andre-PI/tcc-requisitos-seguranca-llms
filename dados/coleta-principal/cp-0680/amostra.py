import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(os.environ.get("TCC_ARQUIVOS_DIR", "")).resolve()


@app.get("/download")
async def download_arquivo(nome: str = Query(...)):
    # Normaliza e resolve o caminho solicitado
    caminho_solicitado = (BASE_DIR / nome).resolve()

    # Previne Directory Traversal (OWASP Path Traversal)
    if not caminho_solicitado.is_relative_to(BASE_DIR):
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    # Verifica se o arquivo existe e se é um arquivo regular
    if not caminho_solicitado.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return FileResponse(
        path=caminho_solicitado,
        media_type="application/octet-stream",
        filename=caminho_solicitado.name,
    )