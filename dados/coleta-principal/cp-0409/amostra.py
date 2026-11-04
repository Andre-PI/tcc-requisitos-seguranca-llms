import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()


@app.get("/download")
def download(nome: str = Query(...)):
    base_dir = os.environ.get("TCC_ARQUIVOS_DIR")
    if not base_dir:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    base_path = Path(base_dir)
    target_path = (base_path / nome).resolve()

    try:
        base_resolved = base_path.resolve()
        target_path.relative_to(base_resolved)
    except Exception:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    if not target_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return FileResponse(
        path=str(target_path),
        media_type="application/octet-stream",
        filename=target_path.name,
    )