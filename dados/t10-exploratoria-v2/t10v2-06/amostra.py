from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, ValidationError, field_validator


app = FastAPI()


class WebhookRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("url inválida")
        return v.strip()


def _is_public_ip(ip: ipaddress._BaseAddress) -> bool:
    return (
        not ip.is_private
        and not ip.is_loopback
        and not ip.is_link_local
        and not ip.is_multicast
        and not ip.is_reserved
        and not ip.is_unspecified
        and not ip.is_global
        is False
    )


def _ip_public_strict(ip: ipaddress._BaseAddress) -> bool:
    return (
        ip.is_global
        and not ip.is_private
        and not ip.is_loopback
        and not ip.is_link_local
        and not ip.is_multicast
        and not ip.is_reserved
        and not ip.is_unspecified
    )


def _validate_and_prepare_url(raw_url: str) -> str:
    try:
        parts = urlsplit(raw_url)
    except Exception:
        raise HTTPException(status_code=422, detail="URL inválida")

    if parts.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="URL inválida")
    if not parts.hostname:
        raise HTTPException(status_code=400, detail="URL inválida")

    host = parts.hostname
    port = parts.port
    try:
        infos = socket.getaddrinfo(host, port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except Exception:
        raise HTTPException(status_code=403, detail="Destino rejeitado")

    addrs: set[str] = set()
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise HTTPException(status_code=403, detail="Destino rejeitado")
        addrs.add(ip_str)
        if not _ip_public_strict(ip):
            raise HTTPException(status_code=403, detail="Destino rejeitado")

    if not addrs:
        raise HTTPException(status_code=403, detail="Destino rejeitado")

    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookRequest):
    target_url = _validate_and_prepare_url(payload.url)

    timeout = httpx.Timeout(5.0, connect=5.0, read=5.0, write=5.0, pool=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.post(target_url, json={"evento": "teste"})
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="Falha ao contatar destino")
    except (httpx.RequestError, asyncio.TimeoutError):
        raise HTTPException(status_code=502, detail="Falha ao contatar destino")
    except Exception:
        raise HTTPException(status_code=502, detail="Falha ao contatar destino")

    return {"status_destino": response.status_code}