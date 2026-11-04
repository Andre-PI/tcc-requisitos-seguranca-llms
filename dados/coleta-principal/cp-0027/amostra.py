from __future__ import annotations

import asyncio
import ipaddress
import socket
from contextlib import suppress
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, ValidationError, field_validator


app = FastAPI()


class WebhookTestRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url_scheme_and_host(cls, v: str) -> str:
        try:
            parts = urlsplit(v)
        except Exception:
            raise ValueError("URL inválida")

        if parts.scheme not in {"http", "https"}:
            raise ValueError("Esquema inválido")
        if not parts.hostname:
            raise ValueError("Host ausente")
        return v


def _is_public_ip(ip: ipaddress._BaseAddress) -> bool:
    if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
        return False
    if ip.version == 4:
        if ip.is_reserved or ip.is_global is False:
            return False
        # Reject common metadata/service ranges and special-use ranges
        if ip in ipaddress.ip_network("169.254.0.0/16"):
            return False
    else:
        if ip.is_reserved or ip.is_site_local:
            return False
    return True


def _resolve_and_validate_host(host: str) -> None:
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="URL rejeitada")

    if not infos:
        raise HTTPException(status_code=400, detail="URL rejeitada")

    for family, _, _, _, sockaddr in infos:
        ip_str = sockaddr[0]
        with suppress(ValueError):
            ip = ipaddress.ip_address(ip_str)
            if not _is_public_ip(ip):
                raise HTTPException(status_code=403, detail="URL rejeitada")

    # Rejeita também hosts que resolvem apenas para endereços não públicos
    return


def _build_target_url(original: str) -> str:
    parts = urlsplit(original)
    path = parts.path or "/"
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookTestRequest) -> dict[str, Any]:
    try:
        parts = urlsplit(payload.url)
    except Exception:
        raise HTTPException(status_code=422, detail="URL inválida")

    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise HTTPException(status_code=422, detail="URL inválida")

    _resolve_and_validate_host(parts.hostname)

    target_url = _build_target_url(payload.url)

    timeout = httpx.Timeout(5.0, connect=5.0, read=5.0, write=5.0, pool=5.0)
    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=timeout) as client:
            resp = await client.post(target_url, json={"evento": "teste"})
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError, httpx.NetworkError, httpx.TransportError):
        raise HTTPException(status_code=502, detail="Falha ao contatar o destino")
    except Exception:
        raise HTTPException(status_code=502, detail="Falha ao contatar o destino")

    return {"status_destino": resp.status_code}