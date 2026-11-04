import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(os.environ.get("TCC_ARQUIVOS_DIR", "")).resolve()


@app.get("/download")
async def download_arquivo(nome: str = Query(...)):
    if not nome or "\x00" in nome:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    caminho_relativo = Path(nome)

    if caminho_relativo.is_absolute():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    caminho_alvo = (BASE_DIR / caminho_relativo).resolve()

    try:
        caminho_alvo.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    if not caminho_alvo.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return FileResponse(
        path=caminho_alvo,
        media_type="application/octet-stream",
        filename=caminho_alvo.name,
    )