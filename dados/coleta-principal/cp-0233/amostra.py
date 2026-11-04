from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, ValidationError, field_validator

app = FastAPI()


class WebhookTestRequest(BaseModel):
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def _ensure_http_https(cls, v: Any) -> Any:
        scheme = getattr(v, "scheme", "")
        if scheme not in {"http", "https"}:
            raise ValueError("URL deve usar http ou https")
        if not getattr(v, "host", None):
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
        or ip.is_site_local
        or ip.is_global is False
    )


def _resolve_and_validate_host(host: str) -> None:
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(status_code=422, detail="URL invalida")

    seen = set()
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
            raise HTTPException(status_code=422, detail="URL invalida")
        if not _is_public_ip(ip):
            raise HTTPException(status_code=403, detail="Destino nao permitido")
        has_public = True

    if not has_public:
        raise HTTPException(status_code=403, detail="Destino nao permitido")


def _build_target_url(original_url: HttpUrl) -> str:
    parts = urlsplit(str(original_url))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


@app.post("/webhooks/testar")
def testar_webhook(payload: WebhookTestRequest) -> dict[str, int]:
    url = payload.url
    host = url.host
    assert host is not None

    _resolve_and_validate_host(host)
    target_url = _build_target_url(url)

    try:
        with httpx.Client(
            timeout=httpx.Timeout(5.0, connect=5.0, read=5.0, write=5.0, pool=5.0),
            follow_redirects=False,
        ) as client:
            response = client.post(target_url, json={"evento": "teste"})
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Falha ao contatar destino")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Falha ao contatar destino")

    return {"status_destino": response.status_code}