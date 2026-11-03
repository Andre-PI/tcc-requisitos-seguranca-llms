import os
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

ALLOWED_MIME_TYPES = {"image/png", "image/jpeg"}
ALLOWED_FORMATS = {"PNG", "JPEG"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MiB


def _get_upload_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR não definido")
    path = Path(base).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        raise RuntimeError("TCC_UPLOAD_DIR inválido")
    return path


def _safe_extension(image_format: str) -> str:
    return ".png" if image_format == "PNG" else ".jpg"


def _sanitize_original_name(name: str) -> str:
    name = Path(name).name
    name = name.strip()
    if not name:
        return ""
    return re.sub(r"[\x00-\x1f\x7f]", "", name)


@app.post("/foto")
async def upload_foto(arquivo: UploadFile = File(...)):
    if arquivo.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=415, detail="Formato de imagem não suportado")

    upload_dir = _get_upload_dir()

    original_name = _sanitize_original_name(arquivo.filename or "")
    original_suffix = Path(original_name).suffix.lower()

    try:
        data = await arquivo.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await arquivo.close()

    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo muito grande")

    try:
        with Image.open(__import__("io").BytesIO(data)) as img:
            img.load()
            image_format = img.format
            if image_format not in ALLOWED_FORMATS:
                raise HTTPException(status_code=415, detail="Formato de imagem não suportado")

            if image_format == "PNG":
                mode = "RGBA" if "A" in img.getbands() else "RGB"
                if img.mode not in ("RGB", "RGBA", "L", "P"):
                    img = img.convert(mode)
            elif image_format == "JPEG":
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")

            ext = _safe_extension(image_format)
            unique_name = f"{uuid.uuid4().hex}{ext}"
            out_path = upload_dir / unique_name

            save_kwargs = {}
            if image_format == "JPEG":
                save_kwargs.update({"format": "JPEG", "quality": 95, "optimize": True, "progressive": True})
            else:
                save_kwargs.update({"format": "PNG", "optimize": True})

            img.save(out_path, **save_kwargs)

    except UnidentifiedImageError:
        raise HTTPException(status_code=415, detail="Arquivo inválido ou corrompido")
    except OSError:
        raise HTTPException(status_code=400, detail="Não foi possível processar a imagem")

    return JSONResponse(status_code=201, content={"arquivo": unique_name})