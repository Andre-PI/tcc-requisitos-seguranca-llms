import os
import re
import uuid
import tempfile
from pathlib import Path
from typing import Final

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI()

ALLOWED_FORMATS: Final[set[str]] = {"PNG", "JPEG"}
MAX_UPLOAD_BYTES: Final[int] = 20 * 1024 * 1024  # 20 MiB
CHUNK_SIZE: Final[int] = 1024 * 1024  # 1 MiB

_SAFE_BASENAME_RE = re.compile(r"[^A-Za-z0-9.\- _()\[\]{}@+=,;!~'áàâãäçéèêëíìîïñóòôõöúùûüÁÀÂÃÄÇÉÈÊËÍÌÎÏÑÓÒÔÕÖÚÙÛÜß]+", re.UNICODE)


def _upload_dir() -> Path:
    raw = os.environ.get("TCC_UPLOAD_DIR")
    if not raw:
        raise RuntimeError("TCC_UPLOAD_DIR não definida no ambiente")
    path = Path(raw).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir():
        raise RuntimeError("TCC_UPLOAD_DIR não é um diretório válido")
    return path


def _sanitize_base_name(name: str) -> str:
    name = name.strip().replace("\x00", "")
    if not name:
        return "arquivo"
    name = Path(name).name
    name = _SAFE_BASENAME_RE.sub("_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name or "arquivo"


def _detect_format_and_validate(temp_path: Path) -> str:
    try:
        with Image.open(temp_path) as img:
            img.verify()
        with Image.open(temp_path) as img:
            fmt = (img.format or "").upper()
            if fmt not in ALLOWED_FORMATS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato inválido. Envie PNG ou JPEG.",
                )
            return fmt
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido ou corrompido.",
        ) from None
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido ou corrompido.",
        ) from None


def _build_output_name(original_name: str, fmt: str) -> str:
    base = _sanitize_base_name(original_name)
    stem = Path(base).stem or "arquivo"
    ext = ".png" if fmt == "PNG" else ".jpg"
    unique = uuid.uuid4().hex
    return f"{stem}_{unique}{ext}"


@app.post("/foto")
async def upload_foto(arquivo: UploadFile = File(...)):
    if not arquivo.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome de arquivo ausente.",
        )

    upload_dir = _upload_dir()
    suffix = Path(arquivo.filename).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato inválido. Envie PNG ou JPEG.",
        )

    tmp_fd, tmp_name = tempfile.mkstemp(prefix="upload_", suffix=suffix)
    tmp_path = Path(tmp_name)

    try:
        total = 0
        with os.fdopen(tmp_fd, "wb") as tmp_file:
            while True:
                chunk = await arquivo.read(CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Arquivo excede o limite permitido.",
                    )
                tmp_file.write(chunk)

        fmt = _detect_format_and_validate(tmp_path)
        output_name = _build_output_name(arquivo.filename, fmt)
        output_path = upload_dir / output_name

        with Image.open(tmp_path) as img:
            if fmt == "PNG":
                img.save(output_path, format="PNG")
            else:
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                img.save(output_path, format="JPEG", quality=95, optimize=True, progressive=True)

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"arquivo": output_name},
        )
    finally:
        try:
            await arquivo.close()
        except Exception:
            pass
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass