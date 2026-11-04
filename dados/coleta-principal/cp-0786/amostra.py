import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image

app = FastAPI()


def _get_upload_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR não definido")
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _unique_filename(original_name: str, content_type: str | None) -> str:
    suffix = Path(original_name).suffix
    if not suffix:
        if content_type == "image/png":
            suffix = ".png"
        elif content_type in ("image/jpeg", "image/jpg"):
            suffix = ".jpg"
    return f"{uuid.uuid4().hex}{suffix}"


@app.post("/foto")
async def upload_foto(arquivo: UploadFile = File(...)):
    content_type = (arquivo.content_type or "").lower()
    if content_type not in {"image/png", "image/jpeg", "image/jpg"}:
        raise HTTPException(status_code=400, detail="Formato de imagem inválido")

    try:
        image = Image.open(arquivo.file)
        image.load()
    except Exception:
        raise HTTPException(status_code=400, detail="Arquivo de imagem inválido")
    finally:
        try:
            arquivo.file.seek(0)
        except Exception:
            pass

    if image.format not in {"PNG", "JPEG"}:
        raise HTTPException(status_code=400, detail="Formato de imagem inválido")

    upload_dir = _get_upload_dir()
    saved_name = _unique_filename(arquivo.filename or "arquivo", content_type)
    target_path = upload_dir / saved_name

    with target_path.open("wb") as out:
        while True:
            chunk = await arquivo.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)

    await arquivo.close()
    return JSONResponse(status_code=201, content={"arquivo": saved_name})