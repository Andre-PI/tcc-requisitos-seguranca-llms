import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
from pathlib import Path

TCC_ARQUIVOS_DIR = os.environ.get("TCC_ARQUIVOS_DIR")
if not TCC_ARQUIVOS_DIR:
    raise RuntimeError("Variável de ambiente TCC_ARQUIVOS_DIR não definida")

base_dir = Path(TCC_ARQUIVOS_DIR).resolve(strict=True)

app = FastAPI()


@app.get("/download")
async def download(nome: str = Query(...)):
    # Resolve caminho absoluto do arquivo solicitado
    requested_path = (base_dir / nome).resolve()

    # Verifica se o arquivo está dentro do diretório base (prevenção path traversal)
    if not str(requested_path).startswith(str(base_dir) + os.sep):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    if not requested_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    def file_iterator():
        with requested_path.open("rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(file_iterator(), status_code=200, media_type="application/octet-stream")