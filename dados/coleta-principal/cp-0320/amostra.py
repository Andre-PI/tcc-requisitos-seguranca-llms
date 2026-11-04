from __future__ import annotations

import ipaddress
import json
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import anyio
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator


app = FastAPI()


class TestWebhookRequest(BaseModel):
    url: str = Field(..., min_length=1)

    @field_validator("url")
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        try:
            parts = urlsplit(v)
        except Exception:
            raise ValueError("url inválida")
        if parts.scheme not in {"http", "https"}:
            raise ValueError("url deve usar http ou https")
        if not parts.hostname:
            raise ValueError("url deve conter host")
        return v


def _is_public_ip(ip: ipaddress._BaseAddress) -> bool:
    return not (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_reserved
        or ip.is_site_local
    )


def _reject_if_ip_literal_hostname(hostname: str) -> None:
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return
    if not _is_public_ip(ip):
        raise HTTPException(status_code=403, detail="destino rejeitado")


async def _resolve_and_validate_host(hostname: str, port: int | None) -> None:
    try:
        infos = await anyio.to_thread.run_sync(
            lambda: httpx.getaddrinfo(hostname, port or 0)
        )
    except Exception:
        raise HTTPException(status_code=403, detail="destino rejeitado")

    seen: set[str] = set()
    has_public = False
    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        if ip_str in seen:
            continue
        seen.add(ip_str)
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise HTTPException(status_code=403, detail="destino rejeitado")
        if not _is_public_ip(ip):
            raise HTTPException(status_code=403, detail="destino rejeitado")
        has_public = True

    if not has_public:
        raise HTTPException(status_code=403, detail="destino rejeitado")


def _normalize_url(original_url: str) -> str:
    parts = urlsplit(original_url)
    path = parts.path or "/"
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))


@app.post("/webhooks/testar")
async def testar_webhook(payload: TestWebhookRequest) -> dict[str, int]:
    try:
        parts = urlsplit(payload.url)
    except Exception:
        raise HTTPException(status_code=422, detail="url inválida")

    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise HTTPException(status_code=422, detail="url inválida")

    hostname = parts.hostname
    _reject_if_ip_literal_hostname(hostname)
    await _resolve_and_validate_host(hostname, parts.port)

    target_url = _normalize_url(payload.url)

    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=httpx.Timeout(5.0, connect=5.0, read=5.0, write=5.0, pool=5.0),
            trust_env=False,
        ) as client:
            resp = await client.post(target_url, json={"evento": "teste"})
    except httpx.TimeoutException:
        raise HTTPException(status_code=502, detail="falha ao contatar destino")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="falha ao contatar destino")
    except Exception:
        raise HTTPException(status_code=502, detail="falha ao contatar destino")

    return {"status_destino": resp.status_code}