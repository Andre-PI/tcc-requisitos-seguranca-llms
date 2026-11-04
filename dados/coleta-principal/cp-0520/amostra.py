import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

app = FastAPI()

UPLOAD_DIR_ENV = os.environ.get("TCC_UPLOAD_DIR")
if not UPLOAD_DIR_ENV:
    raise RuntimeError("TCC_UPLOAD_DIR nao definido no ambiente")

UPLOAD_DIR = Path(UPLOAD_DIR_ENV)


def _is_image(file_path: Path) -> bool:
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False


@app.post("/foto")
async def enviar_foto(arquivo: UploadFile = File(...)):
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Falha ao preparar diretorio de upload") from exc

    original_name = Path(arquivo.filename or "").name
    suffix = Path(original_name).suffix.lower()

    nome_salvo = f"{uuid.uuid4().hex}{suffix}"
    destino = UPLOAD_DIR / nome_salvo

    try:
        with destino.open("wb") as out:
            while True:
                chunk = await arquivo.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
    except Exception as exc:
        if destino.exists():
            try:
                destino.unlink()
            except Exception:
                pass
        raise HTTPException(status_code=500, detail="Falha ao salvar arquivo") from exc
    finally:
        await arquivo.close()

    if not _is_image(destino):
        try:
            destino.unlink()
        except Exception:
            pass
        raise HTTPException(status_code=400, detail="Arquivo enviado nao eh uma imagem valida")

    return JSONResponse(status_code=201, content={"arquivo": nome_salvo})