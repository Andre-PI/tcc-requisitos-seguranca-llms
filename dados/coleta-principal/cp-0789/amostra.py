import os
import re
import uuid
import unicodedata
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

_ALLOWED_FORMATS = {"PNG": "png", "JPEG": "jpg", "JPG": "jpg"}
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def _upload_base_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR não definido")
    path = Path(base).expanduser()
    if not path.exists() or not path.is_dir():
        raise RuntimeError("TCC_UPLOAD_DIR inválido")
    return path


def _sanitize_filename(original_name: str, image_format: str) -> str:
    name = unicodedata.normalize("NFKC", original_name).strip()
    name = name.replace("\x00", "")
    name = Path(name).name
    stem = Path(name).stem
    stem = unicodedata.normalize("NFKC", stem).strip()

    safe = []
    for ch in stem:
        cat = unicodedata.category(ch)
        if ch.isalnum() or ch in {" ", "-", "_", "."} or cat.startswith("L") or cat.startswith("N"):
            safe.append(ch)
        else:
            safe.append("_")
    stem = "".join(safe).strip(" ._")
    stem = re.sub(r"\s+", " ", stem)

    if not stem:
        stem = f"foto-{uuid.uuid4().hex}"

    ext = _ALLOWED_FORMATS[image_format]
    return f"{stem}.{ext}"


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    try:
        base_dir = _upload_base_dir()
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Diretório de upload indisponível")

    try:
        content = await arquivo.read(_MAX_UPLOAD_BYTES + 1)
        if len(content) > _MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Arquivo muito grande")

        try:
            with Image.open(io := __import__("io").BytesIO(content)) as img:
                img.verify()

            with Image.open(__import__("io").BytesIO(content)) as img:
                image_format = (img.format or "").upper()
                if image_format not in _ALLOWED_FORMATS:
                    raise HTTPException(status_code=400, detail="Formato não suportado")
                img.load()
                safe_name = _sanitize_filename(arquivo.filename or "foto", image_format)
                target = base_dir / safe_name

                suffix = target.suffix
                stem = target.stem
                counter = 1
                while target.exists():
                    target = base_dir / f"{stem}-{counter}{suffix}"
                    counter += 1

                tmp_name = f".{target.name}.tmp-{uuid.uuid4().hex}"
                tmp_path = base_dir / tmp_name

                save_kwargs = {}
                if image_format == "JPEG" and img.mode not in ("RGB", "L", "CMYK"):
                    img = img.convert("RGB")

                img.save(tmp_path, format=image_format, **save_kwargs)
                os.replace(tmp_path, target)

        except UnidentifiedImageError:
            raise HTTPException(status_code=400, detail="Arquivo inválido")
        except OSError:
            raise HTTPException(status_code=400, detail="Arquivo inválido")

        return JSONResponse(status_code=201, content={"arquivo": target.name})

    finally:
        await arquivo.close()