import os
import uuid
from io import BytesIO
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image

app = FastAPI()


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    upload_dir = os.environ.get("TCC_UPLOAD_DIR", ".")
    os.makedirs(upload_dir, exist_ok=True)

    contents = await arquivo.read()

    try:
        image = Image.open(BytesIO(contents))
        img_format = image.format
        if img_format not in ("JPEG", "PNG"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de imagem inválido. Suportados apenas JPEG e PNG.",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido ou corrompido.",
        )

    ext = ".jpg" if img_format == "JPEG" else ".png"

    orig_name = arquivo.filename or ""
    orig_base = os.path.splitext(os.path.basename(orig_name))[0].strip()

    unique_id = uuid.uuid4().hex
    if orig_base:
        nome_salvo = f"{unique_id}_{orig_base}{ext}"
    else:
        nome_salvo = f"{unique_id}{ext}"

    caminho_completo = os.path.join(upload_dir, nome_salvo)
    with open(caminho_completo, "wb") as f:
        f.write(contents)

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": nome_salvo})