import os
import re
import uuid
import tempfile
from pathlib import Path
from typing import Final

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

MAX_UPLOAD_BYTES: Final[int] = 20 * 1024 * 1024
ALLOWED_FORMATS: Final[set[str]] = {"PNG", "JPEG"}


def _upload_dir() -> Path:
    raw = os.environ.get("TCC_UPLOAD_DIR")
    if not raw:
        raise RuntimeError("TCC_UPLOAD_DIR não definida")
    base = Path(raw)
    base.mkdir(parents=True, exist_ok=True)
    if not base.is_dir():
        raise RuntimeError("TCC_UPLOAD_DIR não é um diretório")
    return base


def _sanitize_original_name(name: str) -> str:
    name = Path(name).name.strip()
    if not name:
        return "arquivo"
    name = re.sub(r"[\x00-\x1f\x7f]", "_", name)
    return name


def _extension_for_format(fmt: str) -> str:
    return ".png" if fmt == "PNG" else ".jpg"


@app.post("/foto")
async def upload_foto(arquivo: UploadFile = File(...)):
    base_dir = _upload_dir()

    try:
        data = await arquivo.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await arquivo.close()

    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio")

    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo muito grande")

    try:
        with Image.open(tempfile.SpooledTemporaryFile()) as _:
            pass
    except Exception:
        pass

    try:
        image = Image.open(tempfile.SpooledTemporaryFile())
    except Exception:
        image = None

    try:
        from io import BytesIO

        bio = BytesIO(data)
        with Image.open(bio) as img:
            img.load()
            if img.format not in ALLOWED_FORMATS:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato inválido")

            ext = _extension_for_format(img.format)
            safe_original = _sanitize_original_name(arquivo.filename or "arquivo")
            stem = Path(safe_original).stem or "arquivo"
            unique_name = f"{stem}_{uuid.uuid4().hex}{ext}"
            target = base_dir / unique_name

            tmp_fd, tmp_path = tempfile.mkstemp(dir=str(base_dir), prefix=".upload-", suffix=ext)
            try:
                with os.fdopen(tmp_fd, "wb") as tmp_file:
                    tmp_file.write(data)
                    tmp_file.flush()
                    os.fsync(tmp_file.fileno())
                os.replace(tmp_path, target)
            finally:
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                except OSError:
                    pass

            return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": unique_name})
    except UnidentifiedImageError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo não é uma imagem válida")
    except OSError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao salvar arquivo")