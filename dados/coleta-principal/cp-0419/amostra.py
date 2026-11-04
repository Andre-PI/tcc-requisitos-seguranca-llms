import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

app = FastAPI()


def _get_base_dir() -> Path:
    base = os.environ.get("TCC_ARQUIVOS_DIR")
    if not base:
        raise RuntimeError("TCC_ARQUIVOS_DIR not configured")
    return Path(base).expanduser().resolve(strict=True)


BASE_DIR = _get_base_dir()


def _safe_resolve(nome: str) -> Path:
    if nome is None or nome == "":
        raise HTTPException(status_code=400, detail="Parametro 'nome' invalido")

    candidate = (BASE_DIR / nome).resolve(strict=False)

    try:
        candidate.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=400, detail="Parametro 'nome' invalido")

    return candidate


@app.get("/download")
def download(nome: str = Query(...)):
    path = _safe_resolve(nome)

    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    try:
        data = path.read_bytes()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")
    except OSError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    filename = path.name
    headers = {
        "Content-Disposition": f'attachment; filename="{filename.replace(chr(34), chr(95))}"'
    }
    return Response(content=data, media_type="application/octet-stream", headers=headers)