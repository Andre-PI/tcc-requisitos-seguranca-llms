import os
from pathlib import Path
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse


app = FastAPI()

BASE_DIR_RAW = os.environ.get("TCC_ARQUIVOS_DIR")
if not BASE_DIR_RAW:
    raise RuntimeError("TCC_ARQUIVOS_DIR nao definida")

BASE_DIR = Path(BASE_DIR_RAW).expanduser().resolve(strict=True)


def _safe_resolve_requested_path(nome: str) -> Path:
    if nome is None or nome == "":
        raise HTTPException(status_code=400, detail="Parametro invalido")

    decoded = unquote(nome)

    # Rejeita caminhos absolutos e qualquer tentativa de escapar via ".."
    requested = Path(decoded)
    if requested.is_absolute():
        raise HTTPException(status_code=400, detail="Parametro invalido")

    for part in requested.parts:
        if part == "..":
            raise HTTPException(status_code=400, detail="Parametro invalido")

    candidate = (BASE_DIR / requested).resolve(strict=False)

    try:
        candidate.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=400, detail="Arquivo fora do diretorio permitido")

    return candidate


@app.get("/download")
def download(nome: str = Query(..., min_length=1)):
    path = _safe_resolve_requested_path(nome)

    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    try:
        return FileResponse(
            path=str(path),
            media_type="application/octet-stream",
            filename=path.name,
        )
    except OSError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")