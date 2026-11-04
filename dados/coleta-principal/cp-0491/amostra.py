import os
import re
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

UPLOAD_DIR_ENV = "TCC_UPLOAD_DIR"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MiB
ALLOWED_FORMATS = {"PNG": ".png", "JPEG": ".jpg", "JPG": ".jpg"}


def _get_upload_dir() -> Path:
    raw = os.environ.get(UPLOAD_DIR_ENV)
    if not raw:
        raise RuntimeError(f"Variável de ambiente {UPLOAD_DIR_ENV} não definida")
    path = Path(raw).expanduser()
    if not path.exists():
        raise RuntimeError(f"Diretório de upload inexistente: {path}")
    if not path.is_dir():
        raise RuntimeError(f"Caminho de upload não é diretório: {path}")
    return path.resolve()


def _sanitize_original_name(name: str) -> str:
    name = Path(name).name
    name = name.replace("\x00", "")
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)
    return name.strip() or "arquivo"


def _validate_and_detect_image(data: bytes) -> tuple[str, str]:
    try:
        with Image.open(__import__("io").BytesIO(data)) as img:
            img.load()
            fmt = (img.format or "").upper()
            if fmt not in ALLOWED_FORMATS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato de imagem inválido. Use PNG ou JPEG.",
                )
            if fmt == "JPEG" and img.mode not in {"RGB", "L", "CMYK", "YCbCr", "RGBA", "LA", "P"}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Imagem JPEG inválida.",
                )
            ext = ALLOWED_FORMATS[fmt]
            return fmt, ext
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo enviado não é uma imagem válida.",
        )
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de imagem corrompido ou inválido.",
        )


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: Annotated[UploadFile, File(...)]) -> JSONResponse:
    if not arquivo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo ausente.")

    content_type = (arquivo.content_type or "").lower()
    if content_type not in {"image/png", "image/jpeg", "image/jpg"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content-Type inválido. Use image/png ou image/jpeg.",
        )

    raw = await arquivo.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Arquivo excede o tamanho máximo permitido.",
        )

    _, ext = _validate_and_detect_image(raw)

    upload_dir = _get_upload_dir()
    original = _sanitize_original_name(arquivo.filename or "arquivo")
    stem = Path(original).stem or "arquivo"
    stem = re.sub(r"[\\/]+", "_", stem).strip() or "arquivo"

    unique_name = f"{stem}_{uuid.uuid4().hex}{ext}"
    destination = upload_dir / unique_name

    try:
        with open(destination, "xb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
    except FileExistsError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao salvar o arquivo.",
        )
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao salvar o arquivo.",
        )

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": unique_name})