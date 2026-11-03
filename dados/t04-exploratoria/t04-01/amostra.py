import os
from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.responses import StreamingResponse
from typing import Optional

app = FastAPI()

BASE_DIR = os.environ.get("TCC_ARQUIVOS_DIR")
if not BASE_DIR:
    raise RuntimeError("Environment variable TCC_ARQUIVOS_DIR not set")
BASE_DIR = os.path.realpath(BASE_DIR)

def is_within_base(path: str, base: str) -> bool:
    try:
        # Resolve real path (symlinks resolved)
        real_path = os.path.realpath(path)
    except Exception:
        return False
    # Must be strictly inside base dir (including base dir itself)
    # Use os.path.commonpath to avoid prefix confusion
    try:
        common = os.path.commonpath([real_path, base])
    except ValueError:
        # Happens if paths are on different drives (unlikely on Linux)
        return False
    return common == base

@app.get("/download")
async def download(nome: str = Query(...)):
    if not nome:
        # nome is required, but Query(...) enforces this
        raise HTTPException(status_code=404)
    # Construct the candidate path relative to base dir
    # Join then resolve to prevent traversal
    requested_path = os.path.join(BASE_DIR, nome)
    if not is_within_base(requested_path, BASE_DIR):
        raise HTTPException(status_code=404)

    if not os.path.isfile(requested_path):
        raise HTTPException(status_code=404)

    try:
        file_size = os.path.getsize(requested_path)
    except Exception:
        # On any failure reading metadata, hide details
        raise HTTPException(status_code=404)

    def iterfile():
        with open(requested_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk

    headers = {"Content-Length": str(file_size)}
    return StreamingResponse(iterfile(), status_code=200, media_type="application/octet-stream", headers=headers)