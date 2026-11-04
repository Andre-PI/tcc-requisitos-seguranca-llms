import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI()

_BASE_DIR = Path(os.environ["TCC_ARQUIVOS_DIR"]).resolve()


def _safe_resolve(nome: str) -> Path:
    if not nome or nome.strip() == "":
        raise HTTPException(status_code=400, detail="Parâmetro 'nome' é obrigatório.")

    candidate = (_BASE_DIR / nome).resolve()

    try:
        candidate.relative_to(_BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=400, detail="Caminho inválido.")

    return candidate


@app.get("/download")
def download(nome: str):
    arquivo = _safe_resolve(nome)

    if not arquivo.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    return FileResponse(path=str(arquivo), filename=arquivo.name, media_type="application/octet-stream")