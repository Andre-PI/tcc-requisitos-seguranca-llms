import os
import uuid
import io
from PIL import Image, ImageOps
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

app = FastAPI()

UPLOAD_DIR = os.getenv("TCC_UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    contents = await arquivo.read(MAX_FILE_SIZE + 1)
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Arquivo excede o tamanho máximo permitido.",
        )

    try:
        with Image.open(io.BytesIO(contents)) as img:
            img_format = img.format
            if img_format not in ("JPEG", "PNG"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato de imagem não suportado. Apenas JPEG e PNG são permitidos.",
                )

            ext = ".jpg" if img_format == "JPEG" else ".png"
            unique_filename = f"{uuid.uuid4().hex}{ext}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)

            real_upload_dir = os.path.realpath(UPLOAD_DIR)
            real_file_path = os.path.realpath(file_path)
            if not real_file_path.startswith(real_upload_dir + os.sep) and real_file_path != real_upload_dir:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Caminho de destino inválido.",
                )

            img = ImageOps.exif_transpose(img)

            if img_format == "JPEG":
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                img.save(file_path, format="JPEG", quality=95)
            else:
                img.save(file_path, format="PNG")

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido ou corrompido.",
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"arquivo": unique_filename},
    )