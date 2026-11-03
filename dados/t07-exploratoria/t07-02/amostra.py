import os
import shlex
import subprocess
from fastapi import FastAPI, Request, HTTPException, status
from pydantic import BaseModel, Field, constr, ValidationError
from typing import Literal

app = FastAPI()

class RelatorioRequest(BaseModel):
    categoria: constr(min_length=1)
    formato: Literal["json", "csv"]

def sanitize_categoria(categoria: str) -> str:
    # Although the categoria is passed as an argument, spaces, accents and apostrophes are allowed,
    # so we must pass it safely as an argument without shell injection.
    # We'll rely on subprocess argument passing (list) to avoid shell injection.
    # No further sanitization needed here.
    return categoria

@app.post("/relatorio", status_code=200)
async def relatorio(req: RelatorioRequest, request: Request):
    util_path = os.getenv("TCC_RELATORIO_UTIL")
    dados_env = os.getenv("TCC_RELATORIO_DADOS", "")
    log_env = os.getenv("TCC_RELATORIO_LOG", "")

    if not util_path or not os.path.isfile(util_path) or not os.access(util_path, os.X_OK):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Relatorio utilitario nao configurado ou inacessivel"
        )

    categoria = sanitize_categoria(req.categoria)
    formato = req.formato

    cmd = [
        os.sys.executable,
        util_path,
        f"--formato",
        formato,
        "--",
        categoria
    ]

    env = os.environ.copy()
    env["TCC_RELATORIO_DADOS"] = dados_env
    env["TCC_RELATORIO_LOG"] = log_env

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Execucao do utilitario expirou"
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao executar o utilitario"
        )

    # Preserve output regardless of return code
    output = proc.stdout or ""

    return {"relatorio": output}