import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(os.environ.get("TCC_ARQUIVOS_DIR", "")).resolve()


@app.get("/download")
def download(nome: str = Query(...)):
    arquivo_path = (BASE_DIR / nome).resolve()

    if not arquivo_path.is_relative_to(BASE_DIR):
        raise HTTPException(status_code=403, detail="Acesso negado.")

    if not arquivo_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado.")

    return FileResponse(path=arquivo_path, filename=arquivo_path.name)