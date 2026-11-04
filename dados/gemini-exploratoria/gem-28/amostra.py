import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR_ENV = os.environ.get("TCC_ARQUIVOS_DIR", "")
BASE_DIR = Path(BASE_DIR_ENV).resolve()


@app.get("/download")
def download(nome: str = Query(...)):
    # Normaliza e sanitiza o caminho relativo
    rel_path = Path(nome.lstrip("/\\"))

    # Monta o caminho candidato sem resolver links ainda
    candidate = (BASE_DIR / rel_path).resolve()

    try:
        # Garante que candidate esteja estritamente contido em BASE_DIR
        candidate.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo nao encontrado",
        )

    if not candidate.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo nao encontrado",
        )

    return FileResponse(
        path=candidate,
        media_type="application/octet-stream",
        filename=candidate.name,
    )