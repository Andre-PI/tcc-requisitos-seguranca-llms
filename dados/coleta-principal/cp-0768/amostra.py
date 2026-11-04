from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator


app = FastAPI(title="Webhook Tester", version="1.0.0")

_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
_LIMITS = httpx.Limits(max_connections=20, max_keepalive_connections=10)


class WebhookTesteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: HttpUrl

    @field_validator("url")
    @classmethod
    def validar_url(cls, v: HttpUrl) -> HttpUrl:
        if v.scheme not in {"http", "https"}:
            raise ValueError("URL deve usar http ou https")
        return v


def _is_private_or_local_address(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False

    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return True
    return False


def _sanitize_and_validate_destination(raw_url: str) -> str:
    parsed = urlsplit(raw_url)

    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="URL inválida")

    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="URL inválida")

    if parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="URL com credenciais não é permitida")

    host = parsed.hostname

    if host.lower() == "localhost" or host.endswith(".local"):
        raise HTTPException(status_code=400, detail="Destino não permitido")

    if _is_private_or_local_address(host):
        raise HTTPException(status_code=400, detail="Destino não permitido")

    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path or "",
            parsed.query or "",
            "",
        )
    )


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookTesteRequest) -> dict[str, Any]:
    destino = _sanitize_and_validate_destination(str(payload.url))

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, limits=_LIMITS, follow_redirects=False) as client:
            response = await client.post(destino, json={"evento": "teste"})
    except (httpx.RequestError, httpx.TimeoutException, socket.gaierror) as exc:
        raise HTTPException(status_code=502, detail="Destino não pôde ser contatado") from exc

    return {"status_destino": response.status_code}