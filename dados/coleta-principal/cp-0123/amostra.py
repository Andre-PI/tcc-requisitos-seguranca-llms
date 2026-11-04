from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator


app = FastAPI(title="Webhook Tester", version="1.0.0")

DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
MAX_REDIRECTS = 0


class TestarWebhookRequest(BaseModel):
    url: HttpUrl = Field(..., description="URL de destino do webhook")

    @field_validator("url")
    @classmethod
    def validar_esquema(cls, v: HttpUrl) -> HttpUrl:
        scheme = str(v.scheme).lower()
        if scheme not in {"http", "https"}:
            raise ValueError("Esquema de URL inválido")
        return v


def _is_private_or_local_ip(ip: str) -> bool:
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
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Destino inacessível",
        ) from exc

    ips = set()
    for family, _, _, _, sockaddr in infos:
        if family == socket.AF_INET:
            ips.add(sockaddr[0])
        elif family == socket.AF_INET6:
            ips.add(sockaddr[0])

    if not ips:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host de destino inválido",
        )

    for ip in ips:
        if _is_private_or_local_ip(ip):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Destino não permitido",
            )


def _build_target_url(url: HttpUrl) -> str:
    parsed = urlsplit(str(url))
    _resolve_and_validate_host(parsed.hostname or "")
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )


@app.post("/webhooks/testar", status_code=status.HTTP_200_OK)
async def testar_webhook(payload: TestarWebhookRequest) -> dict[str, int]:
    target_url = _build_target_url(payload.url)

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "WebhookTester/1.0",
    }

    try:
        async with httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=False,
            verify=True,
            trust_env=False,
            max_redirects=MAX_REDIRECTS,
        ) as client:
            response = await client.post(
                target_url,
                json={"evento": "teste"},
                headers=headers,
            )
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.RemoteProtocolError, httpx.NetworkError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Destino inacessível",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao contatar o destino",
        ) from exc

    return {"status_destino": int(response.status_code)}