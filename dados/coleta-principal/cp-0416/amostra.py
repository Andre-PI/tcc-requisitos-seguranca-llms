import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

app = FastAPI()


@app.get("/download")
def download(nome: str = Query(...)):
    base_dir = os.environ.get("TCC_ARQUIVOS_DIR")
    if not base_dir:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    base_path = Path(base_dir)
    file_path = (base_path / nome).resolve()

    try:
        base_resolved = base_path.resolve()
        file_path.relative_to(base_resolved)
    except Exception:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return Response(content=file_path.read_bytes(), media_type="application/octet-stream")