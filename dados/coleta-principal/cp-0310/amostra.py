import ipaddress
import socket
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI()


class WebhookTestRequest(BaseModel):
    url: str


def is_safe_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_loopback:
        return False
    if ip.is_private:
        return False
    if ip.is_link_local:
        return False
    if ip.is_multicast:
        return False
    if ip.is_unspecified:
        return False
    if ip.is_reserved:
        return False

    # IPv4 metadata / CGNAT / benchmark / etc.
    if isinstance(ip, ipaddress.IPv4Address):
        # 169.254.0.0/16 is covered by is_link_local
        # 100.64.0.0/10 (CGNAT / Shared Address Space)
        if ip in ipaddress.IPv4Network("100.64.0.0/10"):
            return False
        # 192.0.0.0/24 (IETF Protocol Assignments)
        if ip in ipaddress.IPv4Network("192.0.0.0/24"):
            return False
        # 198.18.0.0/15 (Benchmarking)
        if ip in ipaddress.IPv4Network("198.18.0.0/15"):
            return False
        # 0.0.0.0/8
        if ip in ipaddress.IPv4Network("0.0.0.0/8"):
            return False

    # IPv6 checks
    if isinstance(ip, ipaddress.IPv6Address):
        # IPv4-mapped IPv6 addresses (::ffff:0:0/96)
        if ip.ipv4_mapped:
            return is_safe_ip(ip.ipv4_mapped)
        # IPv4-compatible (::/96)
        if ip.is_site_local:
            return False
        # Unique local (fc00::/7) is covered by is_private

    return ip.is_global


def validate_url(url_str: str) -> None:
    try:
        parsed = urlparse(url_str)
    except Exception:
        raise HTTPException(status_code=400, detail="URL invalida")

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400, detail="Esquema de URL nao permitido"
        )

    host = parsed.hostname
    if not host:
        raise HTTPException(
            status_code=400, detail="Host ausente ou invalido na URL"
        )

    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        addr_infos = socket.getaddrinfo(
            host, port, proto=socket.IPPROTO_TCP
        )
    except Exception:
        raise HTTPException(
            status_code=400, detail="Falha ao resolver host de destino"
        )

    if not addr_infos:
        raise HTTPException(
            status_code=400, detail="Nenhum endereco resolvido para o host"
        )

    for info in addr_infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Endereco IP de destino invalido"
            )

        if not is_safe_ip(ip_obj):
            raise HTTPException(
                status_code=403, detail="Acesso ao endereco de destino negado"
            )


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookTestRequest):
    validate_url(payload.url)

    try:
        async with httpx.AsyncClient(
            follow_redirects=False, timeout=5.0
        ) as client:
            response = await client.post(payload.url, json={"evento": "teste"})
            return {"status_destino": response.status_code}
    except httpx.RequestError:
        raise HTTPException(
            status_code=502, detail="Falha de comunicacao com o destino"
        )