import os
import uuid
from io import BytesIO
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from PIL import Image

app = FastAPI()

upload_dir = os.environ.get("TCC_UPLOAD_DIR", ".")
os.makedirs(upload_dir, exist_ok=True)


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    conteudo = await arquivo.read()

    try:
        imagem = Image.open(BytesIO(conteudo))
        formato = imagem.format
        if formato not in ("JPEG", "PNG"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de imagem inválido. Suportados: PNG, JPEG.",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo não é uma imagem válida.",
        )

    ext = ".jpg" if formato == "JPEG" else ".png"
    if arquivo.filename:
        _, ext_original = os.path.splitext(arquivo.filename)
        if ext_original.lower() in [".jpg", ".jpeg", ".png"]:
            ext = ext_original

    nome_arquivo = f"{uuid.uuid4().hex}{ext}"
    caminho_destino = os.path.join(upload_dir, nome_arquivo)

    with open(caminho_destino, "wb") as f:
        f.write(conteudo)

    return {"arquivo": nome_arquivo}