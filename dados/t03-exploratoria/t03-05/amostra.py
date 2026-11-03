import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image


app = FastAPI()


def _get_upload_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR não definido no ambiente")
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_image_extension(image_format: str) -> str:
    fmt = (image_format or "").upper()
    if fmt == "PNG":
        return ".png"
    if fmt in {"JPEG", "JPG"}:
        return ".jpg"
    raise ValueError("Formato de imagem não suportado")


@app.post("/foto")
async def enviar_foto(arquivo: UploadFile = File(...)):
    if arquivo.content_type not in {"image/png", "image/jpeg"}:
        raise HTTPException(status_code=400, detail="Arquivo deve ser PNG ou JPEG")

    try:
        data = await arquivo.read()
        with Image.open(io := __import__("io").BytesIO(data)) as img:
            img.verify()

        with Image.open(__import__("io").BytesIO(data)) as img:
            ext = _safe_image_extension(img.format)
            nome = f"{uuid.uuid4().hex}{ext}"
            destino = _get_upload_dir() / nome
            img.save(destino)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Imagem inválida")

    return JSONResponse(status_code=201, content={"arquivo": nome})