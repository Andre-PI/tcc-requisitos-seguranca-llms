import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(os.environ.get("TCC_ARQUIVOS_DIR", "")).resolve()


@app.get("/download")
async def download(nome: str = Query(..., min_length=1)):
    try:
        requested_path = (BASE_DIR / nome).resolve()
    except (ValueError, RuntimeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo nao encontrado",
        )

    try:
        if not requested_path.is_relative_to(BASE_DIR):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo nao encontrado",
            )
    except AttributeError:
        if BASE_DIR not in requested_path.parents and requested_path != BASE_DIR:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo nao encontrado",
            )

    if not requested_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo nao encontrado",
        )

    return FileResponse(
        path=requested_path,
        media_type="application/octet-stream",
        filename=requested_path.name,
    )