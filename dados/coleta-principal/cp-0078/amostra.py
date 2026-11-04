import io
import os
import uuid
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 2097152
MAX_WIDTH = 1024
MAX_HEIGHT = 1024
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
ALLOWED_FORMATS = {"PNG", "JPEG"}

app = FastAPI()


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    if not arquivo.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Arquivo invalido.",
        )

    ext = Path(arquivo.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Tipo de arquivo nao suportado.",
        )

    content = bytearray()
    chunk_size = 65536
    while True:
        chunk = await arquivo.read(chunk_size)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > MAX_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Arquivo excede o tamanho maximo permitido.",
            )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio.",
        )

    try:
        with Image.open(io.BytesIO(content)) as img:
            img_format = img.format
            if img_format not in ALLOWED_FORMATS:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Formato de imagem nao permitido.",
                )

            width, height = img.size
            if width > MAX_WIDTH or height > MAX_HEIGHT:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Dimensoes da imagem excedem o limite permitido.",
                )

            img.verify()

        with Image.open(io.BytesIO(content)) as img:
            img.load()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Exception):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Imagem invalida ou corrompida.",
        )

    upload_dir_env = os.environ.get("TCC_UPLOAD_DIR", ".")
    base_dir = Path(upload_dir_env).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    extension_to_use = ".png" if img_format == "PNG" else ".jpg"

    while True:
        filename = f"{uuid.uuid4().hex}{extension_to_use}"
        dest_path = (base_dir / filename).resolve()
        if dest_path.parent != base_dir:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Operacao invalida.",
            )
        if not dest_path.exists():
            break

    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(dest_path, flags, 0o644)
        with os.fdopen(fd, "wb") as f:
            f.write(content)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao salvar a imagem.",
        )

    return {"arquivo": filename}