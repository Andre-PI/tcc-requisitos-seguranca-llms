import os
import io
import uuid
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

app = FastAPI()

UPLOAD_DIR = os.getenv("TCC_UPLOAD_DIR", "/tmp")
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MiB (2097152 bytes)
MAX_WIDTH = 1024
MAX_HEIGHT = 1024
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
ALLOWED_FORMATS = {"PNG", "JPEG"}


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    filename = arquivo.filename or ""
    original_suffix = Path(filename).suffix.lower()

    if not original_suffix or original_suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Extensão de arquivo não permitida. Apenas PNG e JPEG são aceitos."
        )

    content = bytearray()
    chunk_size = 64 * 1024

    while True:
        chunk = await arquivo.read(chunk_size)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="O arquivo excede o tamanho máximo permitido de 2 MiB."
            )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio."
        )

    prefix = bytes(content[:1024]).strip().lower()
    if b"<svg" in prefix or b"<?xml" in prefix:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Tipo de arquivo não permitido."
        )

    try:
        buffer = io.BytesIO(content)
        with Image.open(buffer) as img:
            img_format = img.format
            if not img_format or img_format.upper() not in ALLOWED_FORMATS:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Formato de imagem inválido ou não suportado."
                )

            width, height = img.size
            if width > MAX_WIDTH or height > MAX_HEIGHT:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Dimensões excedem o limite de {MAX_WIDTH}x{MAX_HEIGHT} pixels."
                )

            img.verify()

        buffer.seek(0)
        with Image.open(buffer) as img:
            img.load()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de imagem corrompido ou inválido."
        )

    extension = ".png" if img_format.upper() == "PNG" else ".jpg"

    base_dir = Path(UPLOAD_DIR).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    while True:
        saved_filename = f"{uuid.uuid4().hex}{extension}"
        dest_path = (base_dir / saved_filename).resolve()

        if base_dir not in dest_path.parents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Caminho de gravação inválido."
            )

        if not dest_path.exists():
            break

    try:
        with open(dest_path, "xb") as f:
            f.write(content)
    except FileExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflito na geração do arquivo. Tente novamente."
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao salvar a imagem."
        )

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": saved_filename})