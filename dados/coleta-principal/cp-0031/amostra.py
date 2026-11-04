import os
import uuid
import io
from pathlib import Path
from PIL import Image
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

app = FastAPI()

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MiB (2097152 bytes)
MAX_DIMENSION = 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def get_upload_dir() -> Path:
    env_dir = os.environ.get("TCC_UPLOAD_DIR", "uploads")
    path = Path(env_dir).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    filename = arquivo.filename or ""
    client_ext = Path(filename).suffix.lower()

    if client_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Extensao de arquivo nao suportada. Apenas JPEG e PNG sao permitidos.",
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
                detail="O arquivo excede o limite de 2 MiB.",
            )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio.",
        )

    try:
        image_stream = io.BytesIO(content)
        with Image.open(image_stream) as img:
            img_format = (img.format or "").upper()
            if img_format not in ("JPEG", "PNG"):
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Formato de imagem nao suportado. Apenas JPEG e PNG sao permitidos.",
                )

            width, height = img.size
            if width <= 0 or height <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Dimensoes invalidas.",
                )
            if width > MAX_DIMENSION or height > MAX_DIMENSION:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Dimensoes da imagem excedem o limite de 1024x1024 pixels.",
                )

            img.verify()

        image_stream.seek(0)
        with Image.open(image_stream) as img:
            img.load()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo corrompido ou imagem invalida.",
        )

    ext = ".png" if img_format == "PNG" else ".jpg"

    upload_dir = get_upload_dir()
    while True:
        saved_name = f"{uuid.uuid4().hex}{ext}"
        destination = (upload_dir / saved_name).resolve()
        if not str(destination).startswith(str(upload_dir) + os.sep):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Erro ao processar destino do arquivo.",
            )
        if not destination.exists():
            break

    try:
        destination.write_bytes(content)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao salvar arquivo.",
        )

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": saved_name})