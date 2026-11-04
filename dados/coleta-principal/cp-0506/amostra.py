import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

app = FastAPI()


def _base_dir() -> Path:
    value = os.environ.get("TCC_ARQUIVOS_DIR")
    if not value:
        raise RuntimeError("TCC_ARQUIVOS_DIR nao definida")
    return Path(value)


@app.get("/download")
def download(nome: str = Query(...)):
    base = _base_dir()
    file_path = (base / nome).resolve(strict=False)
    try:
        base_resolved = base.resolve(strict=True)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    try:
        file_path.relative_to(base_resolved)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    content = file_path.read_bytes()
    return Response(content=content, media_type="application/octet-stream")