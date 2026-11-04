import os
import re
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


def _safe_extension(filename: str, content_type: str) -> str:
    name = filename.lower()
    if name.endswith(".png") or content_type == "image/png":
        return ".png"
    if name.endswith(".jpg") or name.endswith(".jpeg") or content_type == "image/jpeg":
        return ".jpg"
    raise HTTPException(status_code=400, detail="Apenas imagens PNG e JPEG são permitidas")


def _validate_image(data: bytes) -> tuple[str, bytes]:
    try:
        with Image.open(__import__("io").BytesIO(data)) as img:
            img.load()
            fmt = (img.format or "").upper()
            if fmt not in {"PNG", "JPEG"}:
                raise HTTPException(status_code=400, detail="Apenas imagens PNG e JPEG são permitidas")
            out = __import__("io").BytesIO()
            if fmt == "PNG":
                img.save(out, format="PNG")
                return ".png", out.getvalue()
            img.save(out, format="JPEG")
            return ".jpg", out.getvalue()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Arquivo de imagem inválido")


@app.post("/foto")
async def upload_foto(arquivo: UploadFile = File(...)):
    upload_dir = _get_upload_dir()

    raw = await arquivo.read()
    ext, image_bytes = _validate_image(raw)

    original_name = Path(arquivo.filename or "").name
    original_ext = _safe_extension(original_name, arquivo.content_type or "")

    final_ext = ext if ext in {".png", ".jpg"} else original_ext
    if final_ext not in {".png", ".jpg"}:
        final_ext = original_ext

    saved_name = f"{uuid.uuid4().hex}{final_ext}"
    target = upload_dir / saved_name

    with open(target, "wb") as f:
        f.write(image_bytes)

    return JSONResponse(status_code=201, content={"arquivo": saved_name})