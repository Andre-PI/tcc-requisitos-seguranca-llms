from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError, field_validator

app = FastAPI()


class WebhookTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(..., min_length=1)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parts = urlsplit(value)

        if parts.scheme not in {"http", "https"}:
            raise ValueError("scheme inválido")
        if not parts.netloc:
            raise ValueError("URL inválida")
        if not parts.hostname:
            raise ValueError("host inválido")

        hostname = parts.hostname.lower()

        if hostname in {"localhost", "localhost."}:
            raise ValueError("host não permitido")

        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
                raise ValueError("endereço não permitido")
        except ValueError:
            # hostname não é IP literal; segue
            pass

        return value


def _resolve_and_block_private_hosts(hostname: str) -> None:
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise HTTPException(status_code=502, detail="destino inacessível") from exc

    seen: set[str] = set()
    for family, _, _, _, sockaddr in infos:
        ip_str = sockaddr[0]
        if ip_str in seen:
            continue
        seen.add(ip_str)

        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            raise HTTPException(status_code=400, detail="destino não permitido")


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookTestRequest) -> dict[str, int]:
    parts = urlsplit(payload.url)

    _resolve_and_block_private_hosts(parts.hostname or "")

    destino = urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path or "",
            parts.query or "",
            parts.fragment or "",
        )
    )

    timeout = httpx.Timeout(10.0, connect=5.0)
    limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            response = await client.post(destino, json={"evento": "teste"})
    except (httpx.RequestError, httpx.TimeoutException) as exc:
        raise HTTPException(status_code=502, detail="destino inacessível") from exc

    return {"status_destino": response.status_code}