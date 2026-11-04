import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(os.environ.get("TCC_ARQUIVOS_DIR", "")).resolve()


@app.get("/download")
async def download(nome: str = Query(...)):
    raw_path = Path(nome)
    if raw_path.is_absolute():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Caminho inválido.",
        )

    target_path = BASE_DIR / raw_path

    try:
        resolved_path = target_path.resolve()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo não encontrado.",
        )

    try:
        resolved_path.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Acesso não permitido.",
        )

    if not resolved_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo não encontrado.",
        )

    return FileResponse(
        path=resolved_path,
        media_type="application/octet-stream",
        filename=resolved_path.name,
    )