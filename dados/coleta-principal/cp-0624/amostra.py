import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = os.environ.get("TCC_ARQUIVOS_DIR")
if not BASE_DIR:
    raise RuntimeError("A variável de ambiente TCC_ARQUIVOS_DIR deve estar definida antes da importação.")

BASE_PATH = Path(BASE_DIR).resolve()


def _safe_resolve(nome: str) -> Path:
    candidate = (BASE_PATH / nome).resolve()
    try:
        candidate.relative_to(BASE_PATH)
    except ValueError:
        raise HTTPException(status_code=400, detail="Caminho inválido.")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    return candidate


@app.get("/download")
def download(nome: str):
    file_path = _safe_resolve(nome)
    return FileResponse(path=str(file_path), filename=file_path.name, media_type="application/octet-stream")