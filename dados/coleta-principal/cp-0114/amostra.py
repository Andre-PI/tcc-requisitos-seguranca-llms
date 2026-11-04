import os
import uuid
import io
from PIL import Image, ImageOps
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

app = FastAPI()

UPLOAD_DIR = os.getenv("TCC_UPLOAD_DIR", "uploads")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_FORMATS = {
    "JPEG": ".jpg",
    "PNG": ".png"
}

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/pjpeg",
    "image/png"
}


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    if arquivo.content_type and arquivo.content_type.lower() not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de arquivo invalido. Apenas imagens JPEG e PNG sao permitidas."
        )

    content = await arquivo.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Arquivo excede o tamanho maximo permitido de 10MB."
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio enviado."
        )

    try:
        image_stream = io.BytesIO(content)
        img = Image.open(image_stream)
        img.verify()

        image_stream.seek(0)
        img = Image.open(image_stream)
        
        image_format = img.format
        if image_format not in ALLOWED_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de imagem nao suportado. Apenas JPEG e PNG sao permitidos."
            )
        
        extension = ALLOWED_FORMATS[image_format]

        # Evita descompressao desnecessaria que altere os bytes se for estritamente valido,
        # mas remove metadata perigosa atraves de sanitizacao mantendo dimensoes e conteudo
        img = ImageOps.exif_transpose(img)
        
        safe_filename = f"{uuid.uuid4().hex}{extension}"
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        dest_path = os.path.join(UPLOAD_DIR, safe_filename)

        if image_format == "JPEG":
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(dest_path, format="JPEG", quality=95)
        elif image_format == "PNG":
            img.save(dest_path, format="PNG")

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Falha ao processar e validar a imagem."
        )
    finally:
        await arquivo.close()

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"arquivo": safe_filename}
    )