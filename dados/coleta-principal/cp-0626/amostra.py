from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, field_validator


app = FastAPI(title="Webhook Tester", version="1.0.0")


class TestarWebhookRequest(BaseModel):
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def validar_esquema(cls, v: HttpUrl) -> HttpUrl:
        if v.scheme not in {"http", "https"}:
            raise ValueError("Esquema de URL inválido")
        return v


def _eh_ip_privado_ou_reservado(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return any(
        (
            addr.is_private,
            addr.is_loopback,
            addr.is_link_local,
            addr.is_multicast,
            addr.is_reserved,
            addr.is_unspecified,
            getattr(addr, "is_site_local", False),
        )
    )


def _validar_destino_seguro(url: str) -> str:
    parsed = urlsplit(url)

    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="URL inválida")

    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="URL inválida")

    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(status_code=502, detail="Destino indisponível") from None

    ips = set()
    for info in infos:
        sockaddr = info[4]
        if sockaddr:
            ips.add(sockaddr[0])

    if not ips:
        raise HTTPException(status_code=400, detail="URL inválida")

    for ip in ips:
        if _eh_ip_privado_ou_reservado(ip):
            raise HTTPException(status_code=400, detail="Destino não permitido")

    return url


def _normalizar_url(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


@app.post("/webhooks/testar")
async def testar_webhook(payload: TestarWebhookRequest) -> dict[str, Any]:
    url = _normalizar_url(str(payload.url))
    _validar_destino_seguro(url)

    timeout = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)
    limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "WebhookTester/1.0",
    }

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=False,
            headers=headers,
        ) as client:
            response = await client.post(url, json={"evento": "teste"})
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.RemoteProtocolError, httpx.NetworkError, OSError):
        raise HTTPException(status_code=502, detail="Destino não pôde ser contatado") from None

    return {"status_destino": response.status_code}