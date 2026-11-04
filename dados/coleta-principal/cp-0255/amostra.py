import os
import re
import uuid
from pathlib import Path
from typing import Final

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

MAX_UPLOAD_BYTES: Final[int] = 10 * 1024 * 1024  # 10 MiB
ALLOWED_FORMATS: Final[set[str]] = {"PNG", "JPEG"}
ALLOWED_CONTENT_TYPES: Final[set[str]] = {"image/png", "image/jpeg"}

UPLOAD_DIR_RAW = os.environ.get("TCC_UPLOAD_DIR")
if not UPLOAD_DIR_RAW:
    raise RuntimeError("A variável de ambiente TCC_UPLOAD_DIR deve estar definida antes da importação.")

UPLOAD_DIR = Path(UPLOAD_DIR_RAW).expanduser().resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._ -]+", re.UNICODE)


def _sanitize_base_name(name: str) -> str:
    name = Path(name).name.strip()
    if not name:
        return "foto"
    name = _SAFE_NAME_RE.sub("_", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = name.rstrip(" .")
    return name or "foto"


def _unique_target_path(original_name: str, ext: str) -> Path:
    base = _sanitize_base_name(original_name)
    stem = Path(base).stem
    candidate = f"{stem}{ext}"
    path = UPLOAD_DIR / candidate
    if not path.exists():
        return path

    for _ in range(1000):
        candidate = f"{stem}_{uuid.uuid4().hex}{ext}"
        path = UPLOAD_DIR / candidate
        if not path.exists():
            return path

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Não foi possível gerar um nome de arquivo único.",
    )


def _validate_and_load_image(data: bytes) -> tuple[Image.Image, str]:
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Arquivo excede o tamanho máximo permitido.",
        )

    try:
        image = Image.open(__import__("io").BytesIO(data))
        image.load()
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido ou formato não suportado.",
        ) from None
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível processar a imagem enviada.",
        ) from None

    fmt = (image.format or "").upper()
    if fmt not in ALLOWED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas imagens PNG e JPEG são aceitas.",
        )

    return image, fmt


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    if arquivo.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas imagens PNG e JPEG são aceitas.",
        )

    data = await arquivo.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio.",
        )

    image, fmt = _validate_and_load_image(data)

    ext = ".png" if fmt == "PNG" else ".jpg"
    target_path = _unique_target_path(arquivo.filename or "foto", ext)

    try:
        if fmt == "PNG":
            image.save(target_path, format="PNG")
        else:
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            image.save(target_path, format="JPEG", quality=95, optimize=True, progressive=True)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao salvar o arquivo.",
        ) from None

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": target_path.name})