import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()


@app.get("/download")
def download(nome: str = Query(...)):
    base_dir = os.environ.get("TCC_ARQUIVOS_DIR")
    if not base_dir:
        raise HTTPException(status_code=500, detail="TCC_ARQUIVOS_DIR nao definida")

    base_path = Path(base_dir).resolve(strict=False)
    file_path = (base_path / nome).resolve(strict=False)

    try:
        file_path.relative_to(base_path)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return FileResponse(
        path=str(file_path),
        media_type="application/octet-stream",
        filename=file_path.name,
    )