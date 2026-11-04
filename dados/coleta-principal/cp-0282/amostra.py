import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image

app = FastAPI()


def _upload_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR não definido no ambiente")
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_filename(original: str) -> str:
    name = Path(original).name
    if not name or name in {".", ".."}:
        return f"{uuid.uuid4().hex}"
    return f"{uuid.uuid4().hex}_{name}"


@app.post("/foto")
async def enviar_foto(arquivo: UploadFile = File(...)):
    if not arquivo.filename:
        raise HTTPException(status_code=400, detail="arquivo inválido")

    try:
        data = await arquivo.read()
        if not data:
            raise HTTPException(status_code=400, detail="arquivo vazio")

        try:
            with Image.open(io := __import__("io").BytesIO(data)) as img:
                img.verify()
        except Exception:
            raise HTTPException(status_code=400, detail="arquivo não é uma imagem válida")

        nome_salvo = _safe_filename(arquivo.filename)
        destino = _upload_dir() / nome_salvo

        with open(destino, "wb") as f:
            f.write(data)

        return JSONResponse(status_code=201, content={"arquivo": nome_salvo})
    finally:
        await arquivo.close()