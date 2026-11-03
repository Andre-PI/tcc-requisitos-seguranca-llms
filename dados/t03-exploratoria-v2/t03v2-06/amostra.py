import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from PIL import Image
from pathlib import Path

upload_dir = os.environ.get("TCC_UPLOAD_DIR")
if not upload_dir:
    raise RuntimeError("TCC_UPLOAD_DIR não está definida no ambiente")

upload_path = Path(upload_dir)
upload_path.mkdir(parents=True, exist_ok=True)

app = FastAPI()


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    if arquivo.content_type not in ("image/png", "image/jpeg"):
        raise HTTPException(status_code=400, detail="Formato de arquivo não suportado")

    suffix = ".png" if arquivo.content_type == "image/png" else ".jpg"
    unique_name = f"{uuid.uuid4().hex}{suffix}"
    destino = upload_path / unique_name

    contents = await arquivo.read()
    try:
        with Image.open(BytesIO(contents)) as img:
            img.save(destino)
    except Exception:
        raise HTTPException(status_code=400, detail="Arquivo de imagem inválido")

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"arquivo": unique_name})


from io import BytesIO