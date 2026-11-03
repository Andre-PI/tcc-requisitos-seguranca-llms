from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, field_validator


app = FastAPI()


class WebhookTesteRequest(BaseModel):
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: HttpUrl) -> HttpUrl:
        if v.scheme not in {"http", "https"}:
            raise ValueError("scheme inválido")
        return v


def _is_private_or_local_address(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return any(
        (
            addr.is_private,
            addr.is_loopback,
            addr.is_link_local,
            addr.is_multicast,
            addr.is_reserved,
            addr.is_unspecified,
        )
    )


def _resolve_and_validate_host(host: str) -> None:
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise HTTPException(status_code=502, detail="destino indisponível") from exc

    if not infos:
        raise HTTPException(status_code=502, detail="destino indisponível")

    for family, _, _, _, sockaddr in infos:
        ip = sockaddr[0]
        if _is_private_or_local_address(ip):
            raise HTTPException(status_code=400, detail="URL de destino não permitida")


def _sanitize_and_rebuild_url(raw_url: str) -> str:
    parts = urlsplit(raw_url)

    if parts.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="URL inválida")

    if not parts.hostname:
        raise HTTPException(status_code=400, detail="URL inválida")

    _resolve_and_validate_host(parts.hostname)

    netloc = parts.hostname
    if parts.port is not None:
        netloc = f"{netloc}:{parts.port}"

    return urlunsplit((parts.scheme, netloc, parts.path or "/", parts.query, ""))


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookTesteRequest) -> dict[str, Any]:
    target_url = _sanitize_and_rebuild_url(str(payload.url))

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=False,
            headers={"Content-Type": "application/json"},
        ) as client:
            response = await client.post(target_url, json={"evento": "teste"})
    except (httpx.RequestError, httpx.TimeoutException) as exc:
        raise HTTPException(status_code=502, detail="destino indisponível") from exc

    return {"status_destino": response.status_code}