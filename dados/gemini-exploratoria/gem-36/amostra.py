import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(os.environ["TCC_ARQUIVOS_DIR"]).resolve()


@app.get("/download")
async def download_file(nome: str = Query(..., min_length=1)):
    # Normaliza e previne Path Traversal resolvendo o caminho absoluto
    try:
        requested_path = (BASE_DIR / nome).resolve()
    except Exception:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    # Garante que o caminho final permanece estritamente dentro de BASE_DIR
    try:
        requested_path.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    # Garante que o arquivo existe e é de fato um arquivo regular
    if not requested_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return FileResponse(
        path=requested_path,
        media_type="application/octet-stream",
        filename=requested_path.name,
    )