import os
from pathlib import Path, PurePosixPath
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

app = FastAPI()

_BASE_DIR_RAW = os.environ.get("TCC_ARQUIVOS_DIR")
if not _BASE_DIR_RAW:
    raise RuntimeError("TCC_ARQUIVOS_DIR nao definida")

_BASE_DIR = Path(_BASE_DIR_RAW).expanduser().resolve(strict=True)


def _safe_resolve(nome: str) -> Path:
    if nome is None or nome == "":
        raise HTTPException(status_code=400, detail="Parametro invalido")

    # Reject absolute paths and Windows-style drive paths
    p = PurePosixPath(nome)
    if p.is_absolute() or ":" in nome.split("/")[0]:
        raise HTTPException(status_code=400, detail="Parametro invalido")

    # Build path under base without allowing traversal to escape
    candidate = (_BASE_DIR / Path(*p.parts)).resolve(strict=False)

    try:
        candidate.relative_to(_BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=400, detail="Parametro invalido")

    # Ensure every symlink component stays within base by resolving the final path
    # and checking containment again.
    if candidate.exists():
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Arquivo nao encontrado")
        try:
            resolved.relative_to(_BASE_DIR)
        except ValueError:
            raise HTTPException(status_code=400, detail="Parametro invalido")
        return resolved

    raise HTTPException(status_code=404, detail="Arquivo nao encontrado")


@app.get("/download")
def download(nome: str = Query(...)):
    path = _safe_resolve(nome)

    if not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    try:
        data = path.read_bytes()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")
    except IsADirectoryError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")
    except PermissionError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return Response(content=data, media_type="application/octet-stream")