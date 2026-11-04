import os
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

app = FastAPI()

UPLOAD_DIR = os.environ["TCC_UPLOAD_DIR"]
UPLOAD_PATH = Path(UPLOAD_DIR)


def _safe_filename(original: str) -> str:
    base = Path(original).name
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    if not base:
        base = "arquivo"
    return base


def _validate_image(data: bytes) -> None:
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Arquivo enviado não é uma imagem válida.") from exc


@app.post("/foto")
async def enviar_foto(arquivo: UploadFile = File(...)):
    UPLOAD_PATH.mkdir(parents=True, exist_ok=True)

    conteudo = await arquivo.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    import io

    try:
        with Image.open(io.BytesIO(conteudo)) as img:
            img.verify()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Arquivo enviado não é uma imagem válida.") from exc

    nome_base = _safe_filename(arquivo.filename or "arquivo")
    nome_final = f"{uuid.uuid4().hex}_{nome_base}"
    destino = UPLOAD_PATH / nome_final

    try:
        with open(destino, "wb") as f:
            f.write(conteudo)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Falha ao salvar o arquivo.") from exc

    return JSONResponse(status_code=201, content={"arquivo": nome_final})