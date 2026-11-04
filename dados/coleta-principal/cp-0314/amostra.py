import os
import uuid
from pathlib import Path
from typing import Final

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

MAX_UPLOAD_SIZE: Final[int] = 2 * 1024 * 1024
MAX_DIMENSION: Final[int] = 1024
ALLOWED_EXTENSIONS: Final[set[str]] = {".png", ".jpg", ".jpeg"}


def _upload_base() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR nao definido")
    path = Path(base)
    if not path.exists() or not path.is_dir():
        raise RuntimeError("Diretorio de upload invalido")
    return path


def _safe_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Formato de arquivo nao suportado")
    return suffix


def _validate_image_bytes(data: bytes) -> tuple[str, bytes]:
    if not data:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo excede o limite permitido")

    try:
        with Image.open(io := __import__("io").BytesIO(data)) as img:
            img.verify()
    except UnidentifiedImageError:
        raise HTTPException(status_code=415, detail="Formato de arquivo nao suportado")
    except Exception:
        raise HTTPException(status_code=422, detail="Arquivo corrompido ou invalido")

    try:
        with Image.open(__import__("io").BytesIO(data)) as img:
            img.load()
            width, height = img.size
            mode = img.mode
            fmt = (img.format or "").upper()

            if width <= 0 or height <= 0 or width > MAX_DIMENSION or height > MAX_DIMENSION:
                raise HTTPException(status_code=422, detail="Dimensoes da imagem invalidas")

            if fmt not in {"PNG", "JPEG"}:
                raise HTTPException(status_code=415, detail="Formato de arquivo nao suportado")

            if fmt == "PNG":
                if mode not in {"RGB", "RGBA", "L", "LA", "P"}:
                    raise HTTPException(status_code=422, detail="Arquivo corrompido ou invalido")
            else:
                if mode not in {"RGB", "L", "CMYK", "YCbCr"}:
                    raise HTTPException(status_code=422, detail="Arquivo corrompido ou invalido")

            return fmt, data
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=422, detail="Arquivo corrompido ou invalido")


@app.post("/foto", status_code=201)
async def upload_foto(arquivo: UploadFile = File(...)):
    suffix = _safe_suffix(arquivo.filename or "")
    content = await arquivo.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo excede o limite permitido")

    fmt, valid_bytes = _validate_image_bytes(content)

    base = _upload_base()
    ext = ".png" if fmt == "PNG" else ".jpg"
    while True:
        name = f"{uuid.uuid4().hex}{ext}"
        target = (base / name).resolve()
        if target.parent != base.resolve():
            raise HTTPException(status_code=422, detail="Nome de arquivo invalido")
        if not target.exists():
            break

    try:
        with open(target, "xb") as f:
            f.write(valid_bytes)
    except FileExistsError:
        return await upload_foto(arquivo)
    except Exception:
        raise HTTPException(status_code=422, detail="Falha ao gravar arquivo")

    return JSONResponse(status_code=201, content={"arquivo": name})