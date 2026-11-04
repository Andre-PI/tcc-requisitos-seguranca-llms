import os
import uuid
from pathlib import Path
from PIL import Image
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

app = FastAPI()

UPLOAD_DIR = os.environ.get("TCC_UPLOAD_DIR", ".")


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    content = await arquivo.read()

    try:
        from io import BytesIO

        with Image.open(BytesIO(content)) as img:
            img_format = img.format
            if img_format not in ("JPEG", "PNG"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato de imagem não suportado. Apenas JPEG e PNG são permitidos.",
                )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido ou corrompido.",
        )

    orig_name = arquivo.filename or f"imagem.{img_format.lower()}"
    p = Path(orig_name)
    stem = p.stem
    suffix = p.suffix if p.suffix else f".{img_format.lower()}"

    unique_id = uuid.uuid4().hex
    saved_filename = f"{stem}_{unique_id}{suffix}"

    upload_path = Path(UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)

    dest_path = upload_path / saved_filename
    with open(dest_path, "wb") as f:
        f.write(content)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"arquivo": saved_filename},
    )