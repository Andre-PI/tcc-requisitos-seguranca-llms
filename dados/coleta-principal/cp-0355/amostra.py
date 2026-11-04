import os
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image

app = FastAPI()

UPLOAD_DIR = os.environ.get("TCC_UPLOAD_DIR")
if not UPLOAD_DIR:
    raise RuntimeError("TCC_UPLOAD_DIR não definido no ambiente")

BASE_DIR = Path(UPLOAD_DIR)
BASE_DIR.mkdir(parents=True, exist_ok=True)

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_filename(name: str) -> str:
    name = Path(name).name.strip()
    name = _SAFE_NAME_RE.sub("_", name)
    name = name.strip("._")
    return name or "arquivo"


@app.post("/foto", status_code=201)
async def enviar_foto(arquivo: UploadFile = File(...)):
    original_name = _sanitize_filename(arquivo.filename or "arquivo")
    suffix = Path(original_name).suffix.lower()

    try:
        content = await arquivo.read()
        if not content:
            raise HTTPException(status_code=400, detail="Arquivo vazio")

        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Arquivo muito grande")

        try:
            with Image.open(io_bytes := __import__("io").BytesIO(content)) as img:
                img.verify()
        except Exception:
            raise HTTPException(status_code=400, detail="Arquivo inválido")

        stem = Path(original_name).stem
        if not stem:
            stem = "foto"
        saved_name = f"{stem}_{uuid.uuid4().hex}{suffix or '.img'}"
        target = BASE_DIR / saved_name

        with target.open("xb") as f:
            f.write(content)

        return JSONResponse(status_code=201, content={"arquivo": saved_name})
    finally:
        await arquivo.close()