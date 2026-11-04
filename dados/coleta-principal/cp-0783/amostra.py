import os
import uuid
from io import BytesIO
from pathlib import Path
from PIL import Image
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

app = FastAPI()

UPLOAD_DIR = Path(os.environ.get("TCC_UPLOAD_DIR", "."))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    content = await arquivo.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio"
        )

    try:
        with Image.open(BytesIO(content)) as img:
            img_format = img.format
            if img_format not in ("JPEG", "PNG"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato de imagem não suportado. Apenas JPEG e PNG são permitidos.",
                )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido ou corrompido.",
        )

    ext = ".jpg" if img_format == "JPEG" else ".png"

    original_filename = Path(arquivo.filename or "").name
    original_stem = Path(original_filename).stem if original_filename else "foto"

    unique_suffix = uuid.uuid4().hex
    saved_filename = f"{original_stem}_{unique_suffix}{ext}"
    dest_path = UPLOAD_DIR / saved_filename

    with open(dest_path, "wb") as f:
        f.write(content)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED, content={"arquivo": saved_filename}
    )