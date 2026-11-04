import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = os.environ.get("TCC_ARQUIVOS_DIR")
if not BASE_DIR:
    raise RuntimeError("Variável de ambiente TCC_ARQUIVOS_DIR não definida")

BASE_PATH = Path(BASE_DIR).resolve()


def _resolve_safe_path(nome: str) -> Path:
    if not nome or nome.strip() == "":
        raise HTTPException(status_code=400, detail="Parâmetro 'nome' é obrigatório")

    candidate = (BASE_PATH / nome).resolve()

    try:
        candidate.relative_to(BASE_PATH)
    except ValueError:
        raise HTTPException(status_code=400, detail="Caminho inválido")

    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return candidate


@app.get("/download")
def download(nome: str = Query(..., min_length=1)):
    file_path = _resolve_safe_path(nome)
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )