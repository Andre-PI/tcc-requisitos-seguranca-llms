from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import AnyHttpUrl, BaseModel, Field, ValidationError, field_validator

app = FastAPI(title="Webhook Tester", version="1.0.0")


class WebhookTesteRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)

    @field_validator("url")
    @classmethod
    def validar_url(cls, v: str) -> str:
        try:
            parsed = urlsplit(v)
        except Exception as exc:  # pragma: no cover
            raise ValueError("URL inválida") from exc

        if parsed.scheme not in {"http", "https"}:
            raise ValueError("A URL deve usar http ou https")
        if not parsed.netloc:
            raise ValueError("A URL deve conter host")

        return v


@dataclass(frozen=True)
class Destino:
    scheme: str
    host: str
    port: int
    path: str
    query: str

    @property
    def base_url(self) -> str:
        return f"{self.scheme}://{self.host}:{self.port}"


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
    for info in infos:
        sockaddr = info[4]
        if sockaddr:
            ips.add(sockaddr[0])

    if not ips:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Destino inacessível",
        )

    for ip in ips:
        if _is_private_or_local_ip(ip):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Destino não permitido",
            )


def _normalizar_destino(url: str) -> Destino:
    parsed = urlsplit(url)

    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL inválida",
        )

    if not parsed.hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL inválida",
        )

    _resolve_and_validate_host(parsed.hostname)

    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80

    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"

    return Destino(
        scheme=parsed.scheme,
        host=host,
        port=port,
        path=parsed.path or "/",
        query=parsed.query,
    )


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookTesteRequest, request: Request) -> dict[str, int]:
    destino = _normalizar_destino(payload.url)
    target_url = urlunsplit(
        SplitResult(
            scheme=destino.scheme,
            netloc=f"{destino.host}:{destino.port}",
            path=destino.path,
            query=destino.query,
            fragment="",
        )
    )

    timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "FastAPI-Webhook-Tester/1.0",
    }

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            headers=headers,
            verify=True,
        ) as client:
            resp = await client.post(target_url, json={"evento": "teste"})
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.RemoteProtocolError, httpx.NetworkError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Destino inacessível",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao contatar o destino",
        ) from exc

    return {"status_destino": resp.status_code}