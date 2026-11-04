import os
import uuid
import io
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from PIL import Image, UnidentifiedImageError

app = FastAPI()

UPLOAD_DIR = os.environ.get("TCC_UPLOAD_DIR", "uploads")
MAX_FILE_SIZE = 2 * 1024 * 1024
MAX_WIDTH = 1024
MAX_HEIGHT = 1024

ALLOWED_EXTENSIONS = {
    "PNG": [".png"],
    "JPEG": [".jpg", ".jpeg"],
}


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    if not arquivo.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nome de arquivo invalido ou ausente.",
        )

    client_ext = Path(arquivo.filename).suffix.lower()
    valid_client_exts = {ext for exts in ALLOWED_EXTENSIONS.values() for ext in exts}
    if client_ext not in valid_client_exts:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Extensao de arquivo nao suportada.",
        )

    content = bytearray()
    while chunk := await arquivo.read(65536):
        content.extend(chunk)
        if len(content) > MAX_FILE_SIZE:
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
        image_stream = io.BytesIO(content)
        with Image.open(image_stream) as img:
            format_name = img.format
            if format_name not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Formato de imagem nao suportado.",
                )

            if client_ext not in ALLOWED_EXTENSIONS[format_name]:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Extensao incompativel com o conteudo da imagem.",
                )

            width, height = img.size
            if width > MAX_WIDTH or height > MAX_HEIGHT:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Dimensoes da imagem excedem o limite permitido.",
                )

            img.verify()

        image_stream.seek(0)
        with Image.open(image_stream) as img:
            img.load()

    except (UnidentifiedImageError, SyntaxError):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Arquivo corrompido ou formato nao suportado.",
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Falha ao decodificar a imagem.",
        )

    base_dir = Path(UPLOAD_DIR).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    extension = ".png" if format_name == "PNG" else ".jpg"
    safe_filename = f"{uuid.uuid4().hex}{extension}"
    target_path = (base_dir / safe_filename).resolve()

    if not target_path.is_relative_to(base_dir):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Caminho de gravacao invalido.",
        )

    while target_path.exists():
        safe_filename = f"{uuid.uuid4().hex}{extension}"
        target_path = (base_dir / safe_filename).resolve()

    with open(target_path, "wb") as f:
        f.write(content)

    return {"arquivo": safe_filename}