import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, status, Request
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

TCC_UPLOAD_DIR = os.getenv("TCC_UPLOAD_DIR")
if not TCC_UPLOAD_DIR:
    raise RuntimeError("TCC_UPLOAD_DIR environment variable not set")
if not os.path.isdir(TCC_UPLOAD_DIR):
    raise RuntimeError("TCC_UPLOAD_DIR path does not exist or is not a directory")

MAX_SIZE_BYTES = 2_097_152  # 2 MiB
MAX_DIMENSION = 1024
ALLOWED_EXTENSIONS = {".png", ".jpeg", ".jpg"}
ALLOWED_FORMATS = {"PNG", "JPEG"}


def secure_extension(format_name: str) -> str:
    # Map Pillow format to extension (prefer lowercase, jpeg -> jpg)
    if format_name == "JPEG":
        return ".jpg"
    if format_name == "PNG":
        return ".png"
    return ""


@app.exception_handler(HTTPException)
async def http_exc_handler(request: Request, exc: HTTPException):
    # Override to avoid leaking paths or internal info
    content = {"detail": exc.detail}
    return JSONResponse(status_code=exc.status_code, content=content)


@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    # Validate extension from filename
    filename_orig = arquivo.filename
    if not filename_orig or "." not in filename_orig:
        raise HTTPException(status_code=415, detail="Arquivo inválido ou formato não suportado")

    ext = os.path.splitext(filename_orig.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Formato de arquivo não suportado")

    # Read file bytes with size limit
    contents = await arquivo.read(MAX_SIZE_BYTES + 1)
    if not contents:
        raise HTTPException(status_code=400, detail="Arquivo vazio")
    if len(contents) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo muito grande")

    # Validate image content and dimensions with Pillow
    try:
        img = Image.open(io := None)
        # Use BytesIO to open image from bytes
        from io import BytesIO
        io = BytesIO(contents)
        img = Image.open(io)
        img.verify()  # verify corruptions, after verify img needs to be re-opened
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=415, detail="Arquivo não é uma imagem PNG ou JPEG válida")

    # Re-open image after verify to check dimensions and format
    try:
        io.seek(0)
        img = Image.open(io)
    except Exception:
        raise HTTPException(status_code=415, detail="Arquivo corrompido")

    if img.format not in ALLOWED_FORMATS:
        raise HTTPException(status_code=415, detail="Formato de imagem não permitido")

    width, height = img.size
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise HTTPException(status_code=422, detail="Dimensões da imagem excedem o limite permitido")

    # Generate unique filename server-side
    new_name = f"{uuid.uuid4().hex}{secure_extension(img.format)}"
    path = os.path.join(TCC_UPLOAD_DIR, new_name)

    # Save file atomically
    try:
        # Save image in original format to preserve pixel data
        img.save(path, format=img.format)
    except Exception:
        raise HTTPException(status_code=422, detail="Erro ao salvar arquivo")

    return {"arquivo": new_name}