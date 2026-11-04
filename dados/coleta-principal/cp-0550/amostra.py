import os
from pathlib import Path, PurePosixPath
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

app = FastAPI()


def _get_base_dir() -> Path:
    base = os.environ.get("TCC_ARQUIVOS_DIR")
    if not base:
        raise RuntimeError("TCC_ARQUIVOS_DIR nao definido")
    base_path = Path(base).expanduser().resolve(strict=True)
    if not base_path.is_dir():
        raise RuntimeError("TCC_ARQUIVOS_DIR deve apontar para um diretorio")
    return base_path


BASE_DIR = _get_base_dir()


def _safe_resolve_requested_path(nome: str) -> Path:
    if nome is None or nome == "":
        raise HTTPException(status_code=400, detail="Parametro invalido")

    # Rejeita caminhos absolutos e tentativas evidentes de escape
    p = PurePosixPath(nome)
    if p.is_absolute():
        raise HTTPException(status_code=400, detail="Parametro invalido")

    candidate = (BASE_DIR / Path(nome)).resolve(strict=False)

    try:
        candidate.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=400, detail="Arquivo fora do diretorio permitido")

    return candidate


@app.get("/download")
def download(nome: str = Query(...)):
    path = _safe_resolve_requested_path(nome)

    try:
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

        # Garante que links simbolicos nao escapem da base
        resolved = path.resolve(strict=True)
        try:
            resolved.relative_to(BASE_DIR)
        except ValueError:
            raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

        data = resolved.read_bytes()
        return Response(content=data, media_type="application/octet-stream", status_code=200)
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")
    except OSError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")