from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, AnyHttpUrl, Field, ValidationError, field_validator


app = FastAPI(title="Webhook Tester", version="1.0.0")

_TIMEOUT = httpx.Timeout(connect=3.0, read=10.0, write=5.0, pool=5.0)
_LIMITS = httpx.Limits(max_keepalive_connections=0, max_connections=20)


class TesteWebhookRequest(BaseModel):
    url: AnyHttpUrl = Field(..., description="URL de destino do webhook")

    @field_validator("url")
    @classmethod
    def validar_esquema(cls, v: AnyHttpUrl) -> AnyHttpUrl:
        if v.scheme not in {"http", "https"}:
            raise ValueError("A URL deve usar HTTP ou HTTPS.")
        return v


def _is_ip_address(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _resolve_and_validate_host(host: str) -> None:
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Destino indisponível.",
        ) from exc

    ips: set[str] = set()
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        ips.add(sockaddr[0])

    if not ips:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Destino indisponível.",
        )

    for ip_str in ips:
        ip = ipaddress.ip_address(ip_str)
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL de destino não permitida.",
            )


def _sanitizar_url(url: AnyHttpUrl) -> str:
    parsed = urlparse(str(url))
    host = parsed.hostname
    if not host:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL inválida.",
        )

    if _is_ip_address(host):
        ip = ipaddress.ip_address(host)
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL de destino não permitida.",
            )
    else:
        _resolve_and_validate_host(host)

    if parsed.username or parsed.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credenciais na URL não são permitidas.",
        )

    # Preserva caminho e query; remove fragmento por segurança.
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path or "",
            parsed.params,
            parsed.query,
            "",
        )
    )


@app.post("/webhooks/testar")
async def testar_webhook(payload: TesteWebhookRequest) -> dict[str, int]:
    destino = _sanitizar_url(payload.url)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, limits=_LIMITS, follow_redirects=False) as client:
            response = await client.post(destino, json={"evento": "teste"})
    except (httpx.RequestError, httpx.TimeoutException) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível contatar o destino.",
        ) from exc

    return {"status_destino": int(response.status_code)}