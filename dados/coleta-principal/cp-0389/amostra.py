import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR_STR = os.getenv("TCC_ARQUIVOS_DIR", "")
BASE_DIR = Path(BASE_DIR_STR).resolve()


@app.get("/download")
async def download(nome: str = Query(..., min_length=1)):
    # Normaliza caminhos relativos no estilo posix/windows
    clean_nome = nome.lstrip("/\\")
    
    # Resolve o caminho do arquivo solicitado
    try:
        requested_path = (BASE_DIR / clean_nome).resolve()
    except Exception:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    # Proteção contra Path Traversal (OWASP)
    try:
        requested_path.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    # Verifica se o arquivo existe e é de fato um arquivo regular
    if not requested_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    return FileResponse(
        path=requested_path,
        media_type="application/octet-stream",
        filename=requested_path.name,
    )