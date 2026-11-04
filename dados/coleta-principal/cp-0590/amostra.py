import os
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

_ALLOWED_FORMATS = {"PNG": "png", "JPEG": "jpg"}
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MiB


def _get_upload_dir() -> Path:
    raw = os.getenv("TCC_UPLOAD_DIR")
    if not raw:
        raise RuntimeError("TCC_UPLOAD_DIR não definido")
    base = Path(raw)
    if not base.exists():
        raise RuntimeError("TCC_UPLOAD_DIR inexistente")
    if not base.is_dir():
        raise RuntimeError("TCC_UPLOAD_DIR não é diretório")
    return base


def _safe_filename(original_name: str, image_format: str) -> str:
    stem = Path(original_name).stem.strip()
    stem = re.sub(r"[\x00-\x1f\x7f]", "", stem)
    stem = stem.replace("/", "_").replace("\\", "_")
    stem = stem.strip(" .")
    if not stem:
        stem = "foto"

    ext = _ALLOWED_FORMATS[image_format]
    return f"{stem}_{uuid.uuid4().hex}.{ext}"


def _validate_and_normalize_image(data: bytes) -> tuple[bytes, str]:
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Arquivo excede o tamanho máximo permitido",
        )

    try:
        with Image.open(io_bytes := __import__("io").BytesIO(data)) as img:
            img.load()
            fmt = img.format
            if fmt not in _ALLOWED_FORMATS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato de imagem não suportado",
                )

            if fmt == "JPEG":
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                out = __import__("io").BytesIO()
                img.save(out, format="JPEG", quality=95, optimize=True, progressive=True)
                return out.getvalue(), fmt

            if img.mode not in ("RGBA", "RGB", "P", "L"):
                img = img.convert("RGBA")
            out = __import__("io").BytesIO()
            img.save(out, format="PNG", optimize=True)
            return out.getvalue(), fmt

    except UnidentifiedImageError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo enviado não é uma imagem válida",
        )
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível processar a imagem",
        )


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    content_type = (arquivo.content_type or "").lower()
    if content_type not in {"image/png", "image/jpeg"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Somente PNG e JPEG são permitidos",
        )

    raw = await arquivo.read()
    normalized_bytes, fmt = _validate_and_normalize_image(raw)

    upload_dir = _get_upload_dir()
    safe_name = _safe_filename(arquivo.filename or "foto", fmt)
    target = upload_dir / safe_name

    if target.exists():
        safe_name = f"{Path(safe_name).stem}_{uuid.uuid4().hex}{target.suffix}"
        target = upload_dir / safe_name

    try:
        with open(target, "xb") as f:
            f.write(normalized_bytes)
    except FileExistsError:
        safe_name = f"{Path(safe_name).stem}_{uuid.uuid4().hex}{target.suffix}"
        target = upload_dir / safe_name
        with open(target, "xb") as f:
            f.write(normalized_bytes)
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao salvar o arquivo",
        )

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": safe_name})