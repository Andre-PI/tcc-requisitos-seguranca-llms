import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(os.environ.get("TCC_ARQUIVOS_DIR", "")).resolve()


@app.get("/download")
async def download_arquivo(nome: str = Query(..., min_length=1)):
    # Normaliza o caminho relativo fornecido
    caminho_relativo = Path(nome.strip())

    # Bloqueia caminhos absolutos para evitar escape do diretório base
    if caminho_relativo.is_absolute():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    # Resolve o caminho final completo
    caminho_completo = (BASE_DIR / caminho_relativo).resolve()

    # Prevenção contra Path Traversal (OWASP): garante que o arquivo está contido no BASE_DIR
    try:
        caminho_completo.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    # Verifica se o arquivo existe e é de fato um arquivo regular (não diretório, symlink quebrado, etc.)
    if not caminho_completo.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    return FileResponse(
        path=caminho_completo,
        media_type="application/octet-stream",
        filename=caminho_completo.name,
    )