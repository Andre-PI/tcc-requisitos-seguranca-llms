import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()


@app.get("/download")
def download(nome: str = Query(...)):
    base_dir = os.environ.get("TCC_ARQUIVOS_DIR", "")
    base_path = Path(base_dir).resolve()

    file_path = (base_path / nome).resolve()

    try:
        file_path.relative_to(base_path)
    except ValueError:
        raise HTTPException(status_code=404)

    if not file_path.is_file():
        raise HTTPException(status_code=404)

    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        filename=file_path.name,
    )