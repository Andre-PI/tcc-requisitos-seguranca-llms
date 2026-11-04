import ipaddress
import socket
from urllib.parse import urlparse
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class WebhookPayload(BaseModel):
    url: str


def is_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return False

    if isinstance(ip, ipaddress.IPv4Address):
        # CGNAT: 100.64.0.0/10
        if ip in ipaddress.IPv4Network("100.64.0.0/10"):
            return False
        # Link-local / AWS / Cloud metadata: 169.254.0.0/16
        if ip in ipaddress.IPv4Network("169.254.0.0/16"):
            return False
        # TEST-NET networks
        if (
            ip in ipaddress.IPv4Network("192.0.2.0/24")
            or ip in ipaddress.IPv4Network("198.51.100.0/24")
            or ip in ipaddress.IPv4Network("203.0.113.0/24")
            or ip in ipaddress.IPv4Network("198.18.0.0/15")
            or ip in ipaddress.IPv4Network("240.0.0.0/4")
            or ip in ipaddress.IPv4Network("0.0.0.0/8")
        ):
            return False

    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped:
            return is_public_ip(ip.ipv4_mapped)
        if ip.is_site_local:
            return False
        # Unique local address (fc00::/7)
        if ip in ipaddress.IPv6Network("fc00::/7"):
            return False
        # Discard prefix (100::/64)
        if ip in ipaddress.IPv6Network("100::/64"):
            return False
        # Documentation (2001:db8::/32)
        if ip in ipaddress.IPv6Network("2001:db8::/32"):
            return False

    return True


def validate_url(url_str: str) -> None:
    try:
        parsed = urlparse(url_str)
    except Exception:
        raise HTTPException(status_code=400, detail="URL invalida")

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400, detail="Esquema de URL nao permitido"
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="Host ausente na URL")

    # Verificar se o hostname e representacao direta de IP
    try:
        direct_ip = ipaddress.ip_address(hostname)
        if not is_public_ip(direct_ip):
            raise HTTPException(
                status_code=403, detail="Endereco IP de destino nao permitido"
            )
        resolved_ips = [direct_ip]
    except ValueError:
        # Resolver host DNS
        try:
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            addr_info = socket.getaddrinfo(
                hostname, port, proto=socket.IPPROTO_TCP
            )
        except socket.gaierror:
            raise HTTPException(
                status_code=400, detail="Falha na resolucao de nomes do host"
            )

        resolved_ips = []
        for item in addr_info:
            sockaddr = item[4]
            ip_str = sockaddr[0]
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                resolved_ips.append(ip_obj)
            except ValueError:
                raise HTTPException(
                    status_code=403, detail="Endereco IP invalido resolvido"
                )

        if not resolved_ips:
            raise HTTPException(
                status_code=400, detail="Host nao possui enderecos resolviveis"
            )

    for ip_obj in resolved_ips:
        if not is_public_ip(ip_obj):
            raise HTTPException(
                status_code=403, detail="Endereco de destino nao permitido"
            )


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookPayload):
    validate_url(payload.url)

    try:
        async with httpx.AsyncClient(
            follow_redirects=False, timeout=5.0
        ) as client:
            resp = await client.post(payload.url, json={"evento": "teste"})
            return {"status_destino": resp.status_code}
    except (httpx.TimeoutException, httpx.RequestError):
        raise HTTPException(
            status_code=502, detail="Falha ao contatar o destino"
        )
    except Exception:
        raise HTTPException(
            status_code=500, detail="Erro interno no envio da requisicao"
        )