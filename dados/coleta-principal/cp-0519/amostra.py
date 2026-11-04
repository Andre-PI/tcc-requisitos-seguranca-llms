import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

_BASE_DIR_RAW = os.environ.get("TCC_ARQUIVOS_DIR")
if not _BASE_DIR_RAW:
    raise RuntimeError("A variável de ambiente TCC_ARQUIVOS_DIR deve estar definida antes da importação.")

BASE_DIR = Path(_BASE_DIR_RAW).resolve(strict=True)


def _safe_resolve_file(nome: str) -> Path:
    if nome is None:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    rel = Path(nome)

    if rel.is_absolute():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    # Bloqueia tentativas de escape por ".." em qualquer parte do caminho.
    if any(part == ".." for part in rel.parts):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    candidate = (BASE_DIR / rel).resolve(strict=False)

    try:
        candidate.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return candidate


@app.get("/download")
def download(nome: str = Query(..., min_length=1)):
    file_path = _safe_resolve_file(nome)
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )