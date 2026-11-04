import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException

app = FastAPI()


def _get_upload_dir() -> Path:
    base = os.environ.get("TCC_UPLOAD_DIR")
    if not base:
        raise RuntimeError("TCC_UPLOAD_DIR não definido no ambiente")
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_filename(original: str) -> str:
    name = Path(original).name.strip()
    if not name or name in {".", ".."}:
        name = "arquivo"
    suffix = Path(name).suffix
    return f"{uuid.uuid4().hex}{suffix}"


@app.post("/foto", status_code=201)
async def enviar_foto(arquivo: UploadFile = File(...)):
    upload_dir = _get_upload_dir()
    nome_salvo = _safe_filename(arquivo.filename or "arquivo")

    destino = upload_dir / nome_salvo
    try:
        with destino.open("wb") as f:
            while True:
                chunk = await arquivo.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Falha ao salvar o arquivo") from exc
    finally:
        await arquivo.close()

    return {"arquivo": nome_salvo}