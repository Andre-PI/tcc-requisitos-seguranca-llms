import ipaddress
import socket
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, HttpUrl
import httpx

app = FastAPI()


class WebhookPayload(BaseModel):
    url: HttpUrl


def validate_and_resolve_url(target_url: str) -> tuple[str, str]:
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
        addr_infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível resolver o hostname do destino.",
        )

    if not addr_infos:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Endereço IP não encontrado para o destino.",
        )

    for addr_info in addr_infos:
        ip_str = addr_info[4][0]
        ip = ipaddress.ip_address(ip_str)

        if not ip.is_global:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Acesso a endereços de rede privada ou não globais é proibido (SSRF).",
            )

    return hostname, addr_infos[0][4][0]


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookPayload):
    url_str = str(payload.url)
    validate_and_resolve_url(url_str)

    timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.post(
                url_str,
                json={"evento": "teste"},
                headers={"User-Agent": "FastAPI-Webhook-Tester/1.0"},
            )
            return {"status_destino": response.status_code}
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao contatar o servidor de destino.",
        )