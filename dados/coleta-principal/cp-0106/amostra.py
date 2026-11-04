import io
import os
import uuid
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MiB
MAX_WIDTH = 1024
MAX_HEIGHT = 1024
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
ALLOWED_FORMATS = {"PNG", "JPEG"}

upload_dir_env = os.environ.get("TCC_UPLOAD_DIR", ".")
UPLOAD_DIR = Path(upload_dir_env).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI()


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    filename = arquivo.filename or ""
    client_ext = Path(filename).suffix.lower()

    if client_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Extensão de arquivo não permitida. Apenas PNG e JPEG são aceitos.",
        )

    content = bytearray()
    while True:
        chunk = await arquivo.read(65536)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="O arquivo excede o limite máximo permitido de 2 MiB.",
            )

    if not content:
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
                    detail="Formato de imagem não suportado.",
                )

            width, height = img.size
            if width > MAX_WIDTH or height > MAX_HEIGHT:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Dimensões da imagem excedem o limite de {MAX_WIDTH}x{MAX_HEIGHT} pixels.",
                )

            img.verify()

        with Image.open(io.BytesIO(content)) as img:
            img.load()
    except (UnidentifiedImageError, SyntaxError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de imagem inválido ou corrompido.",
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao processar imagem.",
        )

    target_ext = ".png" if img_format == "PNG" else ".jpg"

    while True:
        unique_name = f"{uuid.uuid4().hex}{target_ext}"
        destination = (UPLOAD_DIR / unique_name).resolve()

        if destination.parent != UPLOAD_DIR:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Caminho de gravação inválido.",
            )

        if not destination.exists():
            break

    try:
        with open(destination, "xb") as f:
            f.write(content)
    except FileExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conflito ao salvar o arquivo. Tente novamente.",
        )

    return {"arquivo": unique_name}