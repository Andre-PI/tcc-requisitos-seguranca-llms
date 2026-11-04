import os
import re
import uuid
from pathlib import Path
from typing import Final

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

MAX_UPLOAD_SIZE: Final[int] = 2 * 1024 * 1024
MAX_DIMENSION: Final[int] = 1024
ALLOWED_FORMATS: Final[set[str]] = {"PNG", "JPEG"}
ALLOWED_EXTENSIONS: Final[set[str]] = {".png", ".jpg", ".jpeg"}

INVALID_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _upload_base_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR nao definido")
    return Path(base)


def _safe_extension_from_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in ALLOWED_EXTENSIONS:
        return ".jpg" if suffix == ".jpeg" else suffix
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Extensao nao permitida.",
    )


def _validate_image_bytes(data: bytes, original_filename: str) -> str:
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio.")

    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Arquivo excede o limite permitido.",
        )

    ext = _safe_extension_from_filename(original_filename)

    try:
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            fmt = img.format
            width, height = img.size
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Formato de imagem invalido.",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Arquivo de imagem corrompido.",
        )

    if fmt not in ALLOWED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Formato de imagem nao suportado.",
        )

    if width <= 0 or height <= 0 or width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Dimensoes da imagem fora do permitido.",
        )

    if fmt == "JPEG" and ext not in {".jpg", ".jpeg"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Extensao nao corresponde ao tipo de imagem.",
        )
    if fmt == "PNG" and ext != ".png":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Extensao nao corresponde ao tipo de imagem.",
        )

    return ext


def _generate_filename(ext: str) -> str:
    return f"{uuid.uuid4().hex}{ext}"


def _unique_path(base_dir: Path, ext: str) -> tuple[str, Path]:
    for _ in range(1000):
        name = _generate_filename(ext)
        path = base_dir / name
        if not path.exists():
            return name, path
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Nao foi possivel gerar nome de arquivo.",
    )


def _ensure_within_base(base_dir: Path, candidate: Path) -> None:
    try:
        candidate.relative_to(base_dir)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Caminho invalido.",
        )


def _save_image_bytes(base_dir: Path, data: bytes, ext: str) -> str:
    base_dir.mkdir(parents=True, exist_ok=True)
    name, path = _unique_path(base_dir, ext)
    _ensure_within_base(base_dir, path)

    try:
        with open(path, "xb") as f:
            f.write(data)
    except FileExistsError:
        return _save_image_bytes(base_dir, data, ext)
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nao foi possivel salvar o arquivo.",
        )

    return name


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    data = await arquivo.read()
    ext = _validate_image_bytes(data, arquivo.filename or "")
    base_dir = _upload_base_dir()
    saved_name = _save_image_bytes(base_dir, data, ext)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": saved_name})


import io