import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse

TCC_ARQUIVOS_DIR: str  # deve ser definida antes da importação deste módulo

app = FastAPI()

@app.get("/download")
async def download(nome: str = Query(...)):
    base_dir = os.path.abspath(TCC_ARQUIVOS_DIR)
    requested_path = os.path.normpath(os.path.join(base_dir, nome))
    if not requested_path.startswith(base_dir):
        raise HTTPException(status_code=400, detail="Caminho inválido")
    if not os.path.isfile(requested_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(requested_path, filename=os.path.basename(requested_path), media_type="application/octet-stream")