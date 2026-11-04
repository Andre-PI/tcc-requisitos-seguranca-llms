import ipaddress
import socket
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI()


class WebhookTestRequest(BaseModel):
    url: str


def validate_and_resolve_url(raw_url: str) -> None:
    try:
        parsed = urlparse(raw_url)
    except Exception:
        raise HTTPException(status_code=400, detail="URL invalida")

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400, detail="Apenas esquemas http e https sao permitidos"
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="Host nao informado na URL")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        addr_info = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(
            status_code=400, detail="Nao foi possivel resolver o host informado"
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Erro na resolucao do host")

    if not addr_info:
        raise HTTPException(status_code=400, detail="Nenhum endereco IP resolvido")

    for item in addr_info:
        sockaddr = item[4]
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Endereco IP invalido")

        if (
            not ip_obj.is_global
            or ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        ):
            raise HTTPException(
                status_code=403, detail="Destino nao permitido por politica de seguranca"
            )


@app.post("/webhooks/testar")
async def testar_webhook(dados: WebhookTestRequest):
    validate_and_resolve_url(dados.url)

    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=5.0) as client:
            response = await client.post(dados.url, json={"evento": "teste"})
            return {"status_destino": response.status_code}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=502, detail="Falha ao tentar se conectar ao destino informado"
        )