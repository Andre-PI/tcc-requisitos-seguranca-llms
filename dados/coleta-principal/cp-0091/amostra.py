import os
from pathlib import Path, PurePosixPath

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR_ENV = "TCC_ARQUIVOS_DIR"


def _get_base_dir() -> Path:
    base = os.environ.get(BASE_DIR_ENV)
    if not base:
        raise RuntimeError(f"Environment variable {BASE_DIR_ENV} is not defined")
    base_path = Path(base).expanduser()
    if not base_path.is_absolute():
        base_path = base_path.resolve()
    return base_path


BASE_DIR = _get_base_dir()


def _resolve_safe_path(nome: str) -> Path:
    if nome is None:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    raw = nome.strip()
    if not raw:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    try:
        rel = PurePosixPath(raw)
    except Exception:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    if rel.is_absolute():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    parts = rel.parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    candidate = (BASE_DIR / Path(*parts)).resolve()

    try:
        candidate.relative_to(BASE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return candidate


@app.get("/download")
def download(nome: str = Query(..., min_length=1)):
    file_path = _resolve_safe_path(nome)

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(
        path=str(file_path),
        status_code=200,
        media_type="application/octet-stream",
        filename=file_path.name,
    )