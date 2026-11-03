import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR_RAW = os.getenv("TCC_ARQUIVOS_DIR")
if not BASE_DIR_RAW:
    raise RuntimeError("TCC_ARQUIVOS_DIR nao definido")

BASE_DIR = Path(BASE_DIR_RAW).resolve(strict=True)


def _safe_resolve(user_path: str) -> Path:
    if not user_path or user_path.strip() == "":
        raise HTTPException(status_code=400, detail="Parametro invalido")

    p = Path(user_path)

    if p.is_absolute():
        raise HTTPException(status_code=400, detail="Parametro invalido")

    if any(part == ".." for part in p.parts):
        raise HTTPException(status_code=400, detail="Parametro invalido")

    candidate = (BASE_DIR / p).resolve(strict=False)

    try:
        candidate.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return candidate


@app.get("/download")
def download(nome: str = Query(...)):
    target = _safe_resolve(nome)

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    try:
        return FileResponse(
            path=str(target),
            filename=target.name,
            media_type="application/octet-stream",
        )
    except OSError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")