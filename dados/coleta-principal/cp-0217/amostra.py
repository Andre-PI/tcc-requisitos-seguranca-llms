import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR_STR = os.environ.get("TCC_ARQUIVOS_DIR", "")
BASE_DIR = Path(BASE_DIR_STR).resolve()


@app.get("/download")
def download_arquivo(nome: str = Query(...)):
    clean_nome = nome.lstrip("/\\")
    resolved_base = BASE_DIR.resolve()

    target_path = (resolved_base / clean_nome).resolve()

    try:
        target_path.relative_to(resolved_base)
    except ValueError:
        raise HTTPException(status_code=400, detail="Acesso negado")

    if not target_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return FileResponse(
        path=target_path,
        media_type="application/octet-stream",
        filename=target_path.name,
    )