import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(os.environ.get("TCC_ARQUIVOS_DIR", "")).resolve()


@app.get("/download")
async def download_arquivo(nome: str = Query(..., min_length=1)):
    # Normaliza caminhos separando por barras e remove barras iniciais/finais
    caminho_limpo = nome.lstrip("/\\")

    # Resolve o caminho do arquivo solicitado
    try:
        arquivo_path = (BASE_DIR / caminho_limpo).resolve()
    except Exception:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    # Previne Path Traversal garantindo que o arquivo esta dentro do BASE_DIR
    if not arquivo_path.is_relative_to(BASE_DIR):
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    # Verifica se o arquivo existe e e de fato um arquivo regular
    if not arquivo_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return FileResponse(
        path=arquivo_path,
        media_type="application/octet-stream",
        filename=arquivo_path.name,
    )