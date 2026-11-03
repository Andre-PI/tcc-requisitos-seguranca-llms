import os
import shutil
import imghdr
import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse

app = FastAPI()

UPLOAD_DIR = os.environ.get("TCC_UPLOAD_DIR")
if not UPLOAD_DIR:
    raise RuntimeError("TCC_UPLOAD_DIR environment variable not set")
if not os.path.isdir(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_TYPES = {"png", "jpeg", "jpg"}

def detect_image_type(file_path: str) -> str | None:
    kind = imghdr.what(file_path)
    if kind == "jpeg":
        return "jpeg"
    if kind == "png":
        return "png"
    return None

def secure_filename(filename: str) -> str:
    # Preserve unicode and spaces as required,
    # but remove path separators for security
    filename = filename.replace("/", "_").replace("\\", "_")
    return filename

@app.post("/foto", status_code=status.HTTP_201_CREATED)
async def upload_foto(arquivo: UploadFile = File(...)):
    orig_name = arquivo.filename
    if not orig_name:
        raise HTTPException(status_code=400, detail="Arquivo sem nome")

    # Save to a temporary file to detect type
    tmp_id = uuid.uuid4().hex
    tmp_path = os.path.join(UPLOAD_DIR, f".tmp_{tmp_id}")
    try:
        with open(tmp_path, "wb") as f:
            content = await arquivo.read()
            f.write(content)

        img_type = detect_image_type(tmp_path)
        if img_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail="Arquivo não é PNG ou JPEG válido")

        # Preserve extension according to detected type
        ext = ".png" if img_type == "png" else ".jpg"

        # Sanitize original filename but keep unicode and spaces
        base_name = os.path.splitext(orig_name)[0]
        base_name = secure_filename(base_name)

        # Generate unique filename to ensure independence
        unique_name = f"{base_name}_{tmp_id}{ext}"
        dest_path = os.path.join(UPLOAD_DIR, unique_name)

        # Move temp file to final destination
        shutil.move(tmp_path, dest_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return JSONResponse(status_code=201, content={"arquivo": unique_name})