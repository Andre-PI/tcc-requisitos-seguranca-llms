import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(os.environ.get("TCC_ARQUIVOS_DIR", "")).resolve()


@app.get("/download")
def download(nome: str = Query(...)):
    arquivo_path = (BASE_DIR / nome).resolve()

    if not str(arquivo_path).startswith(str(BASE_DIR)):
        raise HTTPException(status_code=400, detail="Caminho inválido")

    if not arquivo_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(path=arquivo_path, filename=arquivo_path.name)