import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

app = FastAPI()


class WebhookTestRequest(BaseModel):
    url: HttpUrl


class WebhookTestResponse(BaseModel):
    status_destino: int


def is_safe_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    if (
        not ip.is_global
        or ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return False

    # Validação adicional para metadados de nuvem e mapeamento IPv4 em IPv6
    if isinstance(ip, ipaddress.IPv4Address):
        if ip_str.startswith("169.254.") or ip_str.startswith("127."):
            return False
    elif isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped:
            return is_safe_ip(str(ip.ipv4_mapped))

    return True


def validate_destination_host(hostname: str, port: int) -> None:
    try:
        # Se for um literal IP direto
        ip = ipaddress.ip_address(hostname)
        if not is_safe_ip(str(ip)):
            raise HTTPException(
                status_code=400, detail="Destino nao permitido por politica de seguranca."
            )
        return
    except ValueError:
        pass

    try:
        addr_info = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Nao foi possivel resolver o host informado.")

    if not addr_info:
        raise HTTPException(status_code=400, detail="Endereco nao resolvido.")

    for item in addr_info:
        sockaddr = item[4]
        ip_addr = sockaddr[0]
        if not is_safe_ip(ip_addr):
            raise HTTPException(
                status_code=400, detail="Destino nao permitido por politica de seguranca."
            )


@app.post("/webhooks/testar", response_model=WebhookTestResponse)
async def testar_webhook(payload: WebhookTestRequest):
    raw_url = str(payload.url)
    parsed = urlparse(raw_url)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(status_code=400, detail="URL invalida.")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    validate_destination_host(parsed.hostname, port)

    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
            resp = await client.post(raw_url, json={"evento": "teste"})
            return WebhookTestResponse(status_destino=resp.status_code)
    except HTTPException:
        raise
    except httpx.RequestError:
        raise HTTPException(
            status_code=502, detail="Falha ao estabelecer conexao com o destino informado."
        )
    except Exception:
        raise HTTPException(
            status_code=500, detail="Erro interno ao tentar contatar o destino."
        )