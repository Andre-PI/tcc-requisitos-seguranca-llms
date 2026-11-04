import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()


def _get_base_dir() -> Path:
    base = os.environ.get("TCC_ARQUIVOS_DIR")
    if not base:
        raise RuntimeError("TCC_ARQUIVOS_DIR nao definida")
    return Path(base)


@app.get("/download")
def download(nome: str = Query(...)):
    base_dir = _get_base_dir()
    file_path = (base_dir / nome).resolve()

    try:
        base_resolved = base_dir.resolve()
        file_path.relative_to(base_resolved)
    except Exception:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return FileResponse(path=str(file_path), filename=Path(nome).name)