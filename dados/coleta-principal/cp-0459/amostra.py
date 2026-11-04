import io
import os
import uuid
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from PIL import Image

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MiB
MAX_WIDTH = 1024
MAX_HEIGHT = 1024
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
ALLOWED_FORMATS = {"PNG", "JPEG"}

app = FastAPI()


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    if not arquivo.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome de arquivo inválido ou ausente.",
        )

    ext = Path(arquivo.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Formato de arquivo não suportado. Apenas PNG e JPEG são permitidos.",
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
                detail="O arquivo excede o limite máximo permitido de 2 MiB.",
            )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio.",
        )

    try:
        image_stream = io.BytesIO(content)
        with Image.open(image_stream) as img:
            img.verify()
            detected_format = img.format

        if detected_format not in ALLOWED_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Formato de imagem não suportado. Apenas PNG e JPEG são permitidos.",
            )

        image_stream.seek(0)
        with Image.open(image_stream) as img:
            img.load()
            width, height = img.size

        if width > MAX_WIDTH or height > MAX_HEIGHT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dimensões da imagem excedem o limite de {MAX_WIDTH}x{MAX_HEIGHT} pixels.",
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de imagem corrompido ou inválido.",
        )

    upload_dir_env = os.environ.get("TCC_UPLOAD_DIR", ".")
    upload_dir = Path(upload_dir_env).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_extension = ".jpg" if detected_format == "JPEG" else ".png"

    while True:
        unique_name = f"{uuid.uuid4().hex}{file_extension}"
        destination_path = (upload_dir / unique_name).resolve()
        if destination_path.parent != upload_dir:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Operação de gravação inválida.",
            )
        try:
            with open(destination_path, "xb") as f:
                f.write(content)
            break
        except FileExistsError:
            continue

    return {"arquivo": unique_name}