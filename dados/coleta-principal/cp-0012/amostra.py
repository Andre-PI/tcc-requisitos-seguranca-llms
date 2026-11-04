from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl, field_validator

app = FastAPI(title="Webhook Tester", version="1.0.0")


class WebhookTesteRequest(BaseModel):
    url: HttpUrl = Field(..., description="URL do webhook de destino")

    @field_validator("url")
    @classmethod
    def validar_esquema(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme not in {"http", "https"}:
            raise ValueError("Esquema inválido")
        return value


def _is_private_or_local_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def _resolve_and_validate_host(host: str, port: int | None) -> None:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise HTTPException(status_code=502, detail="Destino inacessível") from exc

    if not infos:
        raise HTTPException(status_code=502, detail="Destino inacessível")

    for family, _, _, _, sockaddr in infos:
        ip = sockaddr[0]
        try:
            if _is_private_or_local_ip(ip):
                raise HTTPException(status_code=400, detail="Destino não permitido")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Destino não permitido") from exc


def _rebuild_url_preserving_path_and_query(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Esquema inválido")
    if not parts.hostname:
        raise HTTPException(status_code=400, detail="URL inválida")

    _resolve_and_validate_host(parts.hostname, parts.port)

    netloc = parts.hostname
    if parts.port is not None:
        netloc = f"{netloc}:{parts.port}"
    if parts.username or parts.password:
        raise HTTPException(status_code=400, detail="Credenciais na URL não são permitidas")

    return urlunsplit((parts.scheme, netloc, parts.path or "", parts.query or "", parts.fragment or ""))


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookTesteRequest) -> dict[str, Any]:
    destino = _rebuild_url_preserving_path_and_query(str(payload.url))

    timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
    headers = {"Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            headers=headers,
            trust_env=False,
        ) as client:
            response = await client.post(destino, json={"evento": "teste"})
    except (httpx.RequestError, httpx.TimeoutException) as exc:
        raise HTTPException(status_code=502, detail="Destino inacessível") from exc

    return {"status_destino": response.status_code}