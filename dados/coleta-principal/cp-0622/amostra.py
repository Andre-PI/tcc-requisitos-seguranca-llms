import ipaddress
import socket
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, status
import httpx
from pydantic import BaseModel, HttpUrl


class WebhookTestRequest(BaseModel):
    url: HttpUrl


class WebhookTestResponse(BaseModel):
    status_destino: int


app = FastAPI(title="Webhook Tester API")


def validate_safe_url(target_url: str) -> None:
    parsed = urlsplit(target_url)

    if parsed.scheme.lower() not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esquema de URL inválido. Apenas HTTP e HTTPS são permitidos.",
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host ausente na URL informada.",
        )

    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)

    try:
        addr_info = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível resolver o endereço do host informado.",
        )

    for entry in addr_info:
        ip_str = entry[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
            if not ip.is_global:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Acesso a endereços privados ou restritos é proibido.",
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Endereço IP resolvido inválido.",
            )


@app.post(
    "/webhooks/testar",
    response_model=WebhookTestResponse,
    status_code=status.HTTP_200_OK,
)
async def testar_webhook(dados: WebhookTestRequest):
    target_url = str(dados.url)
    validate_safe_url(target_url)

    payload = {"evento": "teste"}
    timeout = httpx.Timeout(10.0, connect=5.0)

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.post(target_url, json=payload)
            return WebhookTestResponse(status_destino=response.status_code)
    except (httpx.RequestError, httpx.HTTPError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível conectar ao destino informado.",
        )