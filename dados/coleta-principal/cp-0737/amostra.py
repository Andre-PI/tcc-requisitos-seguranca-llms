import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(os.environ["TCC_ARQUIVOS_DIR"]).resolve()


@app.get("/download")
def download(nome: str = Query(...)):
    target_path = Path(nome)
    if target_path.is_absolute():
        relative_path = Path(*target_path.parts[1:])
    else:
        relative_path = target_path

    resolved_path = (BASE_DIR / relative_path).resolve()

    try:
        resolved_path.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")

    if resolved_path == BASE_DIR or not resolved_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=resolved_path,
        media_type="application/octet-stream",
        filename=resolved_path.name,
    )