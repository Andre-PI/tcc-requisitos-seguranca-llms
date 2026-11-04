from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, Field, field_validator


app = FastAPI(title="Webhook Tester", version="1.0.0")


class WebhookTestRequest(BaseModel):
    url: HttpUrl = Field(..., description="URL do webhook a ser testado")

    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: HttpUrl) -> HttpUrl:
        if v.scheme not in {"http", "https"}:
            raise ValueError("A URL deve usar HTTP ou HTTPS")
        return v


@dataclass(frozen=True)
class ResolvedAddress:
    family: int
    sockaddr: tuple[Any, ...]
    ip: str


def _is_private_or_reserved_ip(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    return any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


def _resolve_host(host: str, port: int) -> list[ResolvedAddress]:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise HTTPException(status_code=502, detail="Destino indisponível") from exc

    resolved: list[ResolvedAddress] = []
    seen: set[tuple[int, tuple[Any, ...], str]] = set()

    for family, socktype, proto, canonname, sockaddr in infos:
        ip = sockaddr[0]
        key = (family, sockaddr, ip)
        if key in seen:
            continue
        seen.add(key)
        if _is_private_or_reserved_ip(ip):
            raise HTTPException(status_code=400, detail="Destino não permitido")
        resolved.append(ResolvedAddress(family=family, sockaddr=sockaddr, ip=ip))

    if not resolved:
        raise HTTPException(status_code=502, detail="Destino indisponível")

    return resolved


def _build_target_url(original: HttpUrl) -> str:
    parts = urlsplit(str(original))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookTestRequest) -> dict[str, int]:
    parts = urlsplit(str(payload.url))
    if not parts.hostname:
        raise HTTPException(status_code=400, detail="URL inválida")

    port = parts.port or (443 if parts.scheme == "https" else 80)
    _resolve_host(parts.hostname, port)

    target_url = _build_target_url(payload.url)

    timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
    limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=False,
            headers={"User-Agent": "webhook-tester/1.0"},
            trust_env=False,
        ) as client:
            response = await client.post(target_url, json={"evento": "teste"})
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError, httpx.NetworkError) as exc:
        raise HTTPException(status_code=502, detail="Destino indisponível") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Falha ao contatar destino") from exc

    return {"status_destino": response.status_code}