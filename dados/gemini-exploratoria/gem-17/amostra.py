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
    contents = await arquivo.read()

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Arquivo excede o tamanho máximo permitido.",
        )

    try:
        with Image.open(io.BytesIO(contents)) as img:
            img.verify()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de imagem inválido ou corrompido.",
        )

    try:
        with Image.open(io.BytesIO(contents)) as img:
            format_name = (img.format or "").upper()
            if format_name not in ["JPEG", "PNG"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato de imagem não suportado. Use JPEG ou PNG.",
                )

            ext = ".jpg" if format_name == "JPEG" else ".png"
            filename = f"{uuid.uuid4().hex}{ext}"
            file_path = os.path.join(UPLOAD_DIR, filename)

            # Transpose according to EXIF orientation if applicable
            try:
                processed_img = ImageOps.exif_transpose(img)
            except Exception:
                processed_img = img

            save_format = "JPEG" if format_name == "JPEG" else "PNG"
            if save_format == "JPEG" and processed_img.mode in ("RGBA", "P"):
                processed_img = processed_img.convert("RGB")

            processed_img.save(file_path, format=save_format)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao processar a imagem.",
        )

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": filename})