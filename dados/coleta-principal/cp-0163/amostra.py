import ipaddress
import socket
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, HttpUrl

app = FastAPI()


class WebhookTestRequest(BaseModel):
    url: HttpUrl


class WebhookTestResponse(BaseModel):
    status_destino: int


def validate_target_url(target_url: str) -> None:
    parsed = urlsplit(target_url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esquema de URL inválido. Apenas HTTP e HTTPS são permitidos.",
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL inválida: hostname ausente.",
        )

    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        addr_info_list = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível resolver o hostname fornecido.",
        )

    for entry in addr_info_list:
        ip_str = entry[4][0]
        ip = ipaddress.ip_address(ip_str)

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Endereço de destino não permitido (SSRF mitigação).",
            )


@app.post(
    "/webhooks/testar",
    response_model=WebhookTestResponse,
    status_code=status.HTTP_200_OK,
)
async def testar_webhook(payload: WebhookTestRequest):
    url_str = str(payload.url)
    validate_target_url(url_str)

    timeout = httpx.Timeout(10.0, connect=5.0)

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.post(url_str, json={"evento": "teste"})
            return WebhookTestResponse(status_destino=response.status_code)
    except (httpx.RequestError, httpx.HTTPError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível contatar o destino do webhook.",
        )