import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()


def _upload_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR nao definido no ambiente")
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


@app.post("/foto")
async def enviar_foto(arquivo: UploadFile = File(...)):
    upload_dir = _upload_dir()

    content = await arquivo.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio")

    try:
        with Image.open(__import__("io").BytesIO(content)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo de imagem invalido")

    ext = Path(arquivo.filename or "").suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff"}:
        ext = ".img"

    nome_salvo = f"{uuid.uuid4().hex}{ext}"
    destino = upload_dir / nome_salvo

    with open(destino, "wb") as f:
        f.write(content)

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": nome_salvo})