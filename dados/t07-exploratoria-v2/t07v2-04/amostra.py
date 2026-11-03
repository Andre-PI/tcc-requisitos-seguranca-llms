import os
import sys
import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, constr

class RelatorioRequest(BaseModel):
    categoria: str = Field(..., description="Categoria do relatório")
    formato: constr(regex=r"^(json|csv)$") = Field(..., description="Formato do relatório (json ou csv)")

app = FastAPI()

@app.post("/relatorio")
async def gerar_relatorio(req: RelatorioRequest):
    util_path = os.getenv("TCC_RELATORIO_UTIL")
    if not util_path or not os.path.isfile(util_path) or not os.access(util_path, os.X_OK):
        raise HTTPException(status_code=500, detail="Utilitário de relatório não configurado corretamente")

    env = os.environ.copy()
    # Mantém TCC_RELATORIO_DADOS e TCC_RELATORIO_LOG se existirem
    # (já está preservado pela cópia)
    cmd = [
        sys.executable,
        util_path,
        "--formato", req.formato,
        req.categoria
    ]

    try:
        processo = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            env=env,
            encoding="utf-8",
            errors="replace"
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Erro ao executar o utilitário: {e.stderr.strip() or e.stdout.strip() or str(e)}")

    return {"relatorio": processo.stdout}