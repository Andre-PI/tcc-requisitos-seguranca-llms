import os
import uuid
from io import BytesIO
from pathlib import Path
from PIL import Image
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

app = FastAPI()

UPLOAD_DIR = Path(os.environ.get("TCC_UPLOAD_DIR", "."))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    content = await arquivo.read()
    
    try:
        image = Image.open(BytesIO(content))
        image_format = image.format
        if image_format not in ("JPEG", "PNG"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de imagem inválido. Suportados: JPEG e PNG."
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido ou corrompido."
        )

    original_name = arquivo.filename or "imagem"
    base_stem = Path(original_name).stem or "imagem"
    ext = ".jpg" if image_format == "JPEG" else ".png"
    
    unique_suffix = uuid.uuid4().hex
    saved_filename = f"{base_stem}_{unique_suffix}{ext}"
    dest_path = UPLOAD_DIR / saved_filename

    with open(dest_path, "wb") as f:
        f.write(content)

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": saved_filename})