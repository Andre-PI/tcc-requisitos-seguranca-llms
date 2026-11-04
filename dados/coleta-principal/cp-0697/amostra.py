import os
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

app = FastAPI()


def _get_upload_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR nao definido")
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_filename(original_name: str, content_type: str | None) -> str:
    suffix = Path(original_name).suffix.lower()

    if suffix not in {".png", ".jpg", ".jpeg"}:
        if content_type == "image/png":
            suffix = ".png"
        elif content_type == "image/jpeg":
            suffix = ".jpg"
        else:
            raise HTTPException(status_code=400, detail="Formato de imagem nao suportado")

    return f"{uuid.uuid4().hex}{suffix}"


@app.post("/foto")
async def upload_foto(arquivo: Annotated[UploadFile, File(...)]) -> JSONResponse:
    upload_dir = _get_upload_dir()
    filename = _safe_filename(arquivo.filename or "", arquivo.content_type)

    data = await arquivo.read()
    try:
        with Image.open(__import__("io").BytesIO(data)) as img:
            img.load()
            if img.format not in {"PNG", "JPEG"}:
                raise HTTPException(status_code=400, detail="Formato de imagem nao suportado")

            out_path = upload_dir / filename
            if img.format == "PNG":
                img.save(out_path, format="PNG")
            else:
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                img.save(out_path, format="JPEG")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Arquivo de imagem invalido")

    return JSONResponse(status_code=201, content={"arquivo": filename})