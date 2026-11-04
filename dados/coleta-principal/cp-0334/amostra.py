import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(os.environ.get("TCC_ARQUIVOS_DIR", "")).resolve()


@app.get("/download")
async def download_file(nome: str = Query(..., min_length=1)):
    # Normaliza o caminho relativo removendo eventuais barras iniciais
    relative_path = Path(nome.lstrip("/"))

    try:
        # Resolve o caminho absoluto final
        target_path = (BASE_DIR / relative_path).resolve()
    except (ValueError, RuntimeError):
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    # Previne Path Traversal garantindo que o arquivo está contido em BASE_DIR
    try:
        target_path.relative_to(BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    # Verifica se o caminho existe e é de fato um arquivo regular
    if not target_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    return FileResponse(
        path=target_path,
        media_type="application/octet-stream",
        filename=target_path.name,
    )