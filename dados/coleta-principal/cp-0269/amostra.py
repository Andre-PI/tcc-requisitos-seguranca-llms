from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl, field_validator

app = FastAPI(title="Webhook Tester", version="1.0.0")


class WebhookTesteRequest(BaseModel):
    url: HttpUrl = Field(..., description="URL do webhook de destino")

    @field_validator("url")
    @classmethod
    def validar_esquema(cls, v: HttpUrl) -> HttpUrl:
        if v.scheme not in {"http", "https"}:
            raise ValueError("Esquema inválido")
        return v


def _eh_ip_privado_ou_local(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False

    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return True
    return False


def _validar_destino(url_str: str) -> None:
    parsed = urlparse(url_str)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="URL deve usar http ou https")

    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="URL inválida")

    if _eh_ip_privado_ou_local(parsed.hostname):
        raise HTTPException(status_code=400, detail="Destino não permitido")


def _reconstruir_url(url_str: str) -> str:
    parsed = urlparse(url_str)
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path or "",
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookTesteRequest) -> dict[str, int]:
    url = str(payload.url)
    _validar_destino(url)

    destino = _reconstruir_url(url)

    timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
    limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": "WebhookTester/1.0"},
        ) as client:
            resp = await client.post(destino, json={"evento": "teste"})
    except (httpx.RequestError, httpx.TimeoutException, socket.gaierror) as exc:
        raise HTTPException(status_code=502, detail="Destino não pôde ser contatado") from exc

    return {"status_destino": resp.status_code}