import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR_STR = os.environ.get("TCC_ARQUIVOS_DIR", "")
BASE_DIR = Path(BASE_DIR_STR).resolve()


@app.get("/download")
def download_arquivo(nome: str = Query(...)):
    target_rel = nome.lstrip("/\\")
    candidate_path = (BASE_DIR / target_rel).resolve()

    try:
        candidate_path.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo nao encontrado",
        )

    if not candidate_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo nao encontrado",
        )

    return FileResponse(
        path=candidate_path,
        media_type="application/octet-stream",
        filename=candidate_path.name,
    )