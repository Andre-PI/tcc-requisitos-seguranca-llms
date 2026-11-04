import os
from pathlib import Path, PurePosixPath

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()


def _get_base_dir() -> Path:
    base = os.environ.get("TCC_ARQUIVOS_DIR")
    if not base:
        raise RuntimeError("TCC_ARQUIVOS_DIR nao definida")
    return Path(base).resolve(strict=True)


BASE_DIR = _get_base_dir()


def _safe_resolve(requested_name: str) -> Path:
    if requested_name is None:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    candidate = PurePosixPath(requested_name)

    if candidate.is_absolute() or any(part in ("", ".", "..") for part in candidate.parts):
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    target = (BASE_DIR / Path(*candidate.parts)).resolve(strict=False)

    try:
        target.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return target


@app.get("/download")
def download(nome: str = Query(..., min_length=1)):
    target = _safe_resolve(nome)

    if not target.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return FileResponse(
        path=str(target),
        media_type="application/octet-stream",
        filename=target.name,
    )