import ipaddress
import socket
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, HttpUrl
import httpx

app = FastAPI()


class WebhookTestRequest(BaseModel):
    url: HttpUrl


class WebhookTestResponse(BaseModel):
    status_destino: int


def is_safe_ip(ip_str: str) -> bool:
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


def validate_target_url(target_url: str) -> None:
    parsed = urlparse(target_url)

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esquema de URL inválido. Apenas HTTP e HTTPS são permitidos.",
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hostname ausente na URL.",
        )

    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        addr_info = socket.getaddrinfo(
            hostname, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
        )
    except socket.gaierror:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível resolver o hostname de destino.",
        )

    for entry in addr_info:
        ip = entry[4][0]
        if not is_safe_ip(ip):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Acesso a endereços de rede privada/local não é permitido.",
            )


@app.post(
    "/webhooks/testar",
    response_model=WebhookTestResponse,
    status_code=status.HTTP_200_OK,
)
async def testar_webhook(payload: WebhookTestRequest):
    target_url = str(payload.url)
    validate_target_url(target_url)

    timeout = httpx.Timeout(10.0, connect=5.0)

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.post(
                target_url,
                json={"evento": "teste"},
                headers={"User-Agent": "FastAPI-Webhook-Tester/1.0"},
            )
            return WebhookTestResponse(status_destino=response.status_code)

    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao contatar o destino do webhook.",
        )