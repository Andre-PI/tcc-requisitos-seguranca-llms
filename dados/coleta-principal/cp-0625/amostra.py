import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(os.environ.get("TCC_ARQUIVOS_DIR", "")).resolve()


@app.get("/download")
async def download_file(nome: str = Query(..., min_length=1)):
    # Normaliza caminhos relativos no estilo posix/windows
    safe_relative_path = Path(nome.strip().lstrip("/\\"))

    # Constrói o caminho completo resolvido
    target_path = (BASE_DIR / safe_relative_path).resolve()

    # Previne Directory Traversal / Path Traversal garantindo que o caminho
    # resultante esteja estritamente contido no diretório base permitido
    try:
        target_path.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    # Verifica se o arquivo existe e é de fato um arquivo regular
    if not target_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    return FileResponse(
        path=target_path,
        filename=target_path.name,
        media_type="application/octet-stream",
    )