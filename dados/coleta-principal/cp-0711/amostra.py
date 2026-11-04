import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(os.environ["TCC_ARQUIVOS_DIR"]).resolve()


@app.get("/download")
def download(nome: str = Query(..., min_length=1)):
    caminho = (BASE_DIR / nome).resolve()

    try:
        caminho.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    if not caminho.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(path=str(caminho), filename=caminho.name)