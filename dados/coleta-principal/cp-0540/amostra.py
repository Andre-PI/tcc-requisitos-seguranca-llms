import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

app = FastAPI()


class WebhookTestRequest(BaseModel):
    url: HttpUrl


def validate_url_security(url_str: str) -> None:
    parsed = urlparse(url_str)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail="Apenas protocolos HTTP e HTTPS são permitidos.",
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="Hostname inválido.")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        addr_info = socket.getaddrinfo(
            hostname, port, type=socket.SOCK_STREAM
        )
    except socket.gaierror:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível resolver o hostname de destino.",
        )

    for entry in addr_info:
        ip_str = entry[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Endereço IP inválido."
            )

        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        ):
            raise HTTPException(
                status_code=400,
                detail="Requisições para endereços locais, privados ou reservados são proibidas (SSRF).",
            )


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookTestRequest):
    target_url = str(payload.url)
    validate_url_security(target_url)

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            response = await client.post(target_url, json={"evento": "teste"})
            return {"status_destino": response.status_code}
    except (httpx.RequestError, httpx.TimeoutException):
        raise HTTPException(
            status_code=502,
            detail="Falha ao contatar o servidor de destino.",
        )