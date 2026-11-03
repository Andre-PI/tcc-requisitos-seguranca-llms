import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import Response

app = FastAPI()

BASE_DIR = os.environ.get("TCC_ARQUIVOS_DIR")
if BASE_DIR is None:
    raise RuntimeError("TCC_ARQUIVOS_DIR environment variable is not set")

@app.get("/download")
async def download(nome: str = Query(...)):
    # Caminho absoluto do arquivo solicitado
    caminho = os.path.normpath(os.path.join(BASE_DIR, nome))

    # Garante que o caminho está dentro do diretório base para evitar path traversal
    if not caminho.startswith(os.path.abspath(BASE_DIR) + os.sep):
        raise HTTPException(status_code=404)

    if not os.path.isfile(caminho):
        raise HTTPException(status_code=404)

    try:
        with open(caminho, "rb") as f:
            conteudo = f.read()
    except Exception:
        raise HTTPException(status_code=404)

    return Response(content=conteudo, status_code=200, media_type="application/octet-stream")