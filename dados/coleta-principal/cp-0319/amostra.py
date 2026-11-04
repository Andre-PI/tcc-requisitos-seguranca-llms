import os
import uuid
import io
from PIL import Image, ImageOps
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

app = FastAPI()

UPLOAD_DIR = os.getenv("TCC_UPLOAD_DIR", "/tmp")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    contents = await arquivo.read()

    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio.",
        )

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Arquivo excede o tamanho limite permitido.",
        )

    try:
        image = Image.open(io.BytesIO(contents))
        img_format = image.format
        if img_format not in ("JPEG", "PNG"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de imagem inválido. Suportado apenas PNG e JPEG.",
            )

        # Trata rotação EXIF se presente
        image = ImageOps.exif_transpose(image)
        # Carrega dados para validar integridade completa da imagem
        image.load()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de imagem corrompido ou inválido.",
        )

    ext = ".jpg" if img_format == "JPEG" else ".png"
    safe_filename = f"{uuid.uuid4().hex}{ext}"

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    destination_path = os.path.join(UPLOAD_DIR, safe_filename)

    try:
        if img_format == "JPEG":
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            image.save(destination_path, format="JPEG", quality=95)
        else:
            image.save(destination_path, format="PNG")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao processar e salvar a imagem.",
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"arquivo": safe_filename},
    )