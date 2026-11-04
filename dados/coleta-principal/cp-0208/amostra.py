import os
import uuid
from io import BytesIO
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

UPLOAD_DIR = os.environ.get("TCC_UPLOAD_DIR", "/tmp")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    if not arquivo.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido ou nome ausente.",
        )

    contents = await arquivo.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="O arquivo excede o tamanho máximo permitido.",
        )

    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado está vazio.",
        )

    try:
        with Image.open(BytesIO(contents)) as img:
            img_format = img.format
            if img_format not in ("JPEG", "PNG"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato de imagem não suportado. Apenas PNG e JPEG são permitidos.",
                )

            img.verify()

        with Image.open(BytesIO(contents)) as img:
            ext = ".jpg" if img_format == "JPEG" else ".png"
            filename = f"{uuid.uuid4().hex}{ext}"

            os.makedirs(UPLOAD_DIR, exist_ok=True)
            file_path = os.path.join(UPLOAD_DIR, filename)

            with open(file_path, "wb") as f:
                f.write(contents)

    except (UnidentifiedImageError, SyntaxError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado não é uma imagem válida.",
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao processar e salvar a imagem.",
        )

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": filename})