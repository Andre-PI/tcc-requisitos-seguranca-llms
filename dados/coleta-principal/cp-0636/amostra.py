import ipaddress
import socket
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, HttpUrl

app = FastAPI()


class WebhookRequest(BaseModel):
    url: HttpUrl


def is_ip_allowed(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return not (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        return False


def validate_target_url(url: str) -> None:
    parsed = urlsplit(url)

    if parsed.scheme.lower() not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esquema de URL inválido. Apenas HTTP e HTTPS são permitidos.",
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hostname ausente na URL fornecida.",
        )

    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha na resolução de DNS para o destino informado.",
        )

    for item in addr_info:
        ip_addr = item[4][0]
        if not is_ip_allowed(ip_addr):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso ao endereço IP ou rede de destino não permitido.",
            )


@app.post("/webhooks/testar", status_code=status.HTTP_200_OK)
async def testar_webhook(payload: WebhookRequest):
    url_str = str(payload.url)

    validate_target_url(url_str)

    timeout = httpx.Timeout(10.0, connect=5.0)

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.post(url_str, json={"evento": "teste"})
            return {"status_destino": response.status_code}
    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível estabelecer contato com a URL de destino.",
        )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erro durante o envio da requisição ao destino.",
        )