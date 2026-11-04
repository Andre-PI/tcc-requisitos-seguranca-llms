import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

app = FastAPI()


def _get_base_dir() -> Path:
    base = os.getenv("TCC_ARQUIVOS_DIR")
    if not base:
        raise RuntimeError("TCC_ARQUIVOS_DIR não definido")
    base_path = Path(base).expanduser().resolve(strict=True)
    if not base_path.is_dir():
        raise RuntimeError("TCC_ARQUIVOS_DIR inválido")
    return base_path


BASE_DIR = _get_base_dir()


def _safe_resolve_under_base(nome: str) -> Path:
    if nome is None or nome == "":
        raise HTTPException(status_code=400, detail="Parâmetro inválido")

    requested = Path(nome)

    # Reject absolute paths and drive-qualified paths on all platforms.
    if requested.is_absolute() or requested.drive:
        raise HTTPException(status_code=400, detail="Parâmetro inválido")

    # Resolve against base and prevent traversal outside base.
    candidate = (BASE_DIR / requested).resolve(strict=False)

    try:
        candidate.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return candidate


@app.get("/download")
def download(nome: str = Query(...)):
    path = _safe_resolve_under_base(nome)

    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    try:
        content = path.read_bytes()
    except OSError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return Response(
        content=content,
        media_type="application/octet-stream",
        status_code=200,
    )