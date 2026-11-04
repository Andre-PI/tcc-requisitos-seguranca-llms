import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(os.environ.get("TCC_ARQUIVOS_DIR", "")).resolve()


@app.get("/download")
async def download(nome: str = Query(..., min_length=1)):
    # Normaliza caminhos que comecem com barras para prevenir que sobreponham a base
    sanitized_nome = nome.lstrip("/\\")

    caminho_solicitado = BASE_DIR.joinpath(sanitized_nome)

    try:
        caminho_resolvido = caminho_solicitado.resolve()
    except (OSError, RuntimeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo nao encontrado",
        )

    # Verifica se o caminho resolvido esta contido no diretorio base permitido
    try:
        caminho_resolvido.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo nao encontrado",
        )

    if not caminho_resolvido.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo nao encontrado",
        )

    return FileResponse(
        path=caminho_resolvido,
        media_type="application/octet-stream",
        filename=caminho_resolvido.name,
    )