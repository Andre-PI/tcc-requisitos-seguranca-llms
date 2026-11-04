import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

_BASE_DIR_RAW = os.environ.get("TCC_ARQUIVOS_DIR")
if not _BASE_DIR_RAW:
    raise RuntimeError("TCC_ARQUIVOS_DIR nao definida")

_BASE_DIR = Path(_BASE_DIR_RAW).expanduser().resolve(strict=True)


def _safe_resolve(nome: str) -> Path:
    if nome is None or nome == "":
        raise HTTPException(status_code=400, detail="Parametro 'nome' invalido")

    candidate = Path(nome)

    if candidate.is_absolute():
        raise HTTPException(status_code=400, detail="Caminho invalido")

    # Resolve sem permitir escapar da base; valida cada segmento.
    current = _BASE_DIR
    parts = candidate.parts

    for part in parts:
        if part in ("", "."):
            continue
        if part == "..":
            raise HTTPException(status_code=400, detail="Caminho invalido")

        current = current / part
        try:
            resolved = current.resolve(strict=False)
        except Exception:
            raise HTTPException(status_code=400, detail="Caminho invalido")

        try:
            resolved.relative_to(_BASE_DIR)
        except ValueError:
            raise HTTPException(status_code=400, detail="Caminho invalido")

        current = resolved

    try:
        final_path = current.resolve(strict=True)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")
    except OSError:
        raise HTTPException(status_code=400, detail="Caminho invalido")

    try:
        final_path.relative_to(_BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=400, detail="Caminho invalido")

    return final_path


@app.get("/download")
def download(nome: str = Query(...)):
    path = _safe_resolve(nome)

    if not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return FileResponse(
        path=str(path),
        media_type="application/octet-stream",
        filename=path.name,
    )