from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, AnyHttpUrl, ValidationError, field_validator


app = FastAPI()


class WebhookRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url_scheme_and_host(cls, v: str) -> str:
        try:
            parsed = urlsplit(v)
        except Exception:
            raise ValueError("URL inválida")

        if parsed.scheme not in {"http", "https"}:
            raise ValueError("URL deve usar http ou https")
        if not parsed.hostname:
            raise ValueError("URL deve conter host")
        return v


def _is_public_ip(ip: ipaddress._BaseAddress) -> bool:
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or ip.is_global is False
    )


def _reject_if_ip_literal(host: str) -> None:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return
    if not _is_public_ip(ip):
        raise HTTPException(status_code=400, detail="URL rejeitada")


def _resolve_and_validate_host(host: str, port: int | None) -> None:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(status_code=422, detail="URL inválida")

    addresses: set[str] = set()
    for family, _, _, _, sockaddr in infos:
        if family == socket.AF_INET:
            addresses.add(sockaddr[0])
        elif family == socket.AF_INET6:
            addresses.add(sockaddr[0])

    if not addresses:
        raise HTTPException(status_code=422, detail="URL inválida")

    for addr in addresses:
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            raise HTTPException(status_code=422, detail="URL inválida")
        if not _is_public_ip(ip):
            raise HTTPException(status_code=403, detail="URL rejeitada")


def _build_target_url(original: str) -> str:
    parsed = urlsplit(original)
    host = parsed.hostname
    if not host:
        raise HTTPException(status_code=400, detail="URL rejeitada")

    _reject_if_ip_literal(host)

    port = parsed.port
    _resolve_and_validate_host(host, port)

    netloc = host
    if parsed.port is not None:
        netloc = f"{host}:{parsed.port}"

    return urlunsplit((parsed.scheme, netloc, parsed.path or "", parsed.query or "", ""))


@app.post("/webhooks/testar")
def testar_webhook(payload: WebhookRequest) -> dict[str, Any]:
    try:
        target_url = _build_target_url(payload.url)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=422, detail="URL inválida")

    try:
        with httpx.Client(follow_redirects=False, timeout=5.0) as client:
            response = client.post(target_url, json={"evento": "teste"})
    except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPError):
        raise HTTPException(status_code=502, detail="Falha ao contatar o destino")
    except Exception:
        raise HTTPException(status_code=502, detail="Falha ao contatar o destino")

    return {"status_destino": response.status_code}