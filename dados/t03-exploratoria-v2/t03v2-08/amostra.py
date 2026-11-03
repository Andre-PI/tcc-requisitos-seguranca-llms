import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel


app = FastAPI()


MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_DIMENSION = 1024
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
ALLOWED_FORMATS = {"PNG", "JPEG"}


def _upload_base_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR não definido")
    return Path(base)


def _sanitize_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Formato não suportado")
    return ".jpg" if suffix == ".jpeg" else suffix


def _validate_and_decode_image(data: bytes) -> tuple[str, bytes]:
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio")

    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o limite permitido")

    try:
        with Image.open(io := __import__("io").BytesIO(data)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Imagem inválida ou corrompida")

    try:
        with Image.open(__import__("io").BytesIO(data)) as img:
            fmt = img.format
            if fmt not in ALLOWED_FORMATS:
                raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Formato não suportado")
            if img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Dimensões excedem o limite permitido")
            img.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Imagem inválida ou corrompida")

    return fmt, data


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    _sanitize_extension(arquivo.filename or "")

    content = await arquivo.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o limite permitido")

    fmt, data = _validate_and_decode_image(content)

    base_dir = _upload_base_dir()
    base_dir.mkdir(parents=True, exist_ok=True)

    ext = ".png" if fmt == "PNG" else ".jpg"
    while True:
        name = f"{uuid.uuid4().hex}{ext}"
        target = base_dir / name
        try:
            fd = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
        except Exception:
            try:
                target.unlink(missing_ok=True)
            except Exception:
                pass
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao salvar o arquivo")
        break

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": name})