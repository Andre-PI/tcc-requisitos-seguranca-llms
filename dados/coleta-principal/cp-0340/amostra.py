import os
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


def _safe_filename(original_name: str) -> str:
    suffix = Path(original_name).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}:
        suffix = ".jpg"
    return f"{uuid.uuid4().hex}{suffix}"


@app.post("/foto", status_code=201)
async def enviar_foto(arquivo: UploadFile = File(...)):
    if not arquivo.filename:
        raise HTTPException(status_code=400, detail="Arquivo inválido")

    nome_salvo = _safe_filename(arquivo.filename)
    destino = BASE_DIR / nome_salvo

    try:
        conteudo = await arquivo.read()
        if not conteudo:
            raise HTTPException(status_code=400, detail="Arquivo vazio")

        # Valida se é uma imagem válida
        from io import BytesIO

        with Image.open(BytesIO(conteudo)) as img:
            img.verify()

        destino.write_bytes(conteudo)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Imagem inválida")
    finally:
        await arquivo.close()

    return JSONResponse(status_code=201, content={"arquivo": nome_salvo})