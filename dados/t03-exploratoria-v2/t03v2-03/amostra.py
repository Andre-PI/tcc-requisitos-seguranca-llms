import os
import uuid
import imghdr
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse
from PIL import Image
from typing import Literal

app = FastAPI()

UPLOAD_DIR = os.getenv("TCC_UPLOAD_DIR")
if not UPLOAD_DIR:
    raise RuntimeError("TCC_UPLOAD_DIR environment variable is not set")

upload_path = Path(UPLOAD_DIR)
if not upload_path.is_dir():
    raise RuntimeError(f"TCC_UPLOAD_DIR path does not exist or is not a directory: {UPLOAD_DIR}")


def validate_image_type(data: bytes) -> Literal["jpeg", "png"]:
    kind = imghdr.what(None, h=data)
    if kind == "jpeg":
        return "jpeg"
    if kind == "png":
        return "png"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo deve ser imagem PNG ou JPEG válida")


def secure_filename(filename: str) -> str:
    keepcharacters = (" ", ".", "_", "-")
    filename = filename.strip().replace("\0", "")
    return "".join(c for c in filename if c.isalnum() or c in keepcharacters)


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    contents = await arquivo.read()
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio")

    img_type = validate_image_type(contents)

    # Verify image can be opened and is valid
    try:
        image = Image.open(arquivo.file)
        image.verify()
    except Exception:
        # fallback: try opening from bytes
        try:
            image = Image.open(io.BytesIO(contents))
            image.verify()
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Imagem inválida ou corrompida")

    # Reset file pointer for potential reuse
    await arquivo.seek(0)

    original_name = arquivo.filename or "arquivo"
    original_name = secure_filename(original_name)

    ext = ".jpg" if img_type == "jpeg" else ".png"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    save_path = upload_path / unique_name

    # Save file preserving content and dimensions
    try:
        with open(save_path, "wb") as f:
            f.write(contents)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao salvar arquivo")

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": unique_name})