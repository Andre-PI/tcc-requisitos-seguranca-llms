from __future__ import annotations

import ipaddress
import socket
from typing import Annotated
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, AnyHttpUrl, Field, field_validator

app = FastAPI(title="Webhook Tester", version="1.0.0")

_ALLOWED_SCHEMES = {"http", "https"}
_DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
_MAX_REDIRECTS = 0


class WebhookTesteRequest(BaseModel):
    url: Annotated[AnyHttpUrl, Field(description="URL destino do webhook")]

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: AnyHttpUrl) -> AnyHttpUrl:
        parts = urlsplit(str(v))

        if parts.scheme not in _ALLOWED_SCHEMES:
            raise ValueError("scheme nao permitido")

        if not parts.hostname:
            raise ValueError("host ausente")

        if parts.username or parts.password:
            raise ValueError("userinfo nao permitido")

        if parts.fragment:
            raise ValueError("fragmento nao permitido")

        if not parts.path:
            raise ValueError("caminho ausente")

        host = parts.hostname

        try:
            ipaddress.ip_address(host)
        except ValueError:
            try:
                infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
            except socket.gaierror as exc:
                raise ValueError("host nao resolvivel") from exc

            resolved_ips = set()
            for info in infos:
                sockaddr = info[4]
                ip = sockaddr[0]
                try:
                    resolved_ips.add(ipaddress.ip_address(ip))
                except ValueError:
                    continue

            if not resolved_ips:
                raise ValueError("host nao resolvivel")

            for ip in resolved_ips:
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
                    raise ValueError("destino nao permitido")
        else:
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
            ):
                raise ValueError("destino nao permitido")

        return v


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookTesteRequest) -> dict[str, int]:
    parts = urlsplit(str(payload.url))
    target_url = urlunsplit((parts.scheme, parts.netloc, parts.path or "/", parts.query, ""))

    try:
        async with httpx.AsyncClient(
            timeout=_DEFAULT_TIMEOUT,
            follow_redirects=False,
            max_redirects=_MAX_REDIRECTS,
            headers={"User-Agent": "WebhookTester/1.0"},
            trust_env=False,
        ) as client:
            response = await client.post(target_url, json={"evento": "teste"})
    except (httpx.RequestError, httpx.TimeoutException) as exc:
        raise HTTPException(status_code=502, detail="destino inacessivel") from exc

    return {"status_destino": response.status_code}