import os
import re
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
from io import BytesIO

app = FastAPI()

MAX_BYTES = 2 * 1024 * 1024
MAX_PIXELS = 1024 * 1024
ALLOWED_EXTS = {".png", ".jpg", ".jpeg"}
ALLOWED_FORMATS = {"PNG", "JPEG"}


def _upload_base() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR nao definido")
    p = Path(base)
    if not p.exists() or not p.is_dir():
        raise RuntimeError("Diretorio de upload invalido")
    return p


def _safe_ext(filename: str) -> Optional[str]:
    name = Path(filename).name
    suffix = Path(name).suffix.lower()
    return suffix if suffix in ALLOWED_EXTS else None


def _validate_image_bytes(data: bytes) -> str:
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o limite permitido")

    try:
        with Image.open(BytesIO(data)) as img:
            fmt = img.format
            if fmt not in ALLOWED_FORMATS:
                raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Formato de imagem nao suportado")
            img.verify()

        with Image.open(BytesIO(data)) as img2:
            fmt2 = img2.format
            if fmt2 not in ALLOWED_FORMATS:
                raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Formato de imagem nao suportado")
            w, h = img2.size
            if w <= 0 or h <= 0:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Imagem invalida")
            if w > 1024 or h > 1024 or (w * h) > MAX_PIXELS:
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Dimensoes da imagem excedem o limite permitido")
            img2.load()
    except UnidentifiedImageError:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Arquivo nao e uma imagem PNG ou JPEG valida")
    except OSError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Imagem corrompida ou invalida")

    return "png" if fmt == "PNG" else "jpg"


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    suffix = _safe_ext(arquivo.filename or "")
    if suffix is None:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Extensao nao permitida")

    data = await arquivo.read()
    ext = _validate_image_bytes(data)

    base = _upload_base()
    while True:
        nome_salvo = f"{uuid.uuid4().hex}.{ext}"
        destino = base / nome_salvo
        try:
            fd = os.open(destino, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
            except Exception:
                try:
                    os.unlink(destino)
                except OSError:
                    pass
                raise
            break
        except FileExistsError:
            continue
        except OSError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Falha ao salvar o arquivo")

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": nome_salvo})