import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

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
    if ip.is_reserved:
        return False
    if ip.is_unspecified:
        return False

    if isinstance(ip, ipaddress.IPv4Address):
        # 169.254.0.0/16 (Link local / Metadados AWS/GCP/Azure)
        # 100.64.0.0/10 (Carrier-grade NAT)
        # 192.0.0.0/24 (IETF Protocol Assignments)
        # 198.18.0.0/15 (Benchmarking)
        # 0.0.0.0/8
        if ip in ipaddress.IPv4Network("169.254.0.0/16"):
            return False
        if ip in ipaddress.IPv4Network("100.64.0.0/10"):
            return False
        if ip in ipaddress.IPv4Network("192.0.0.0/24"):
            return False
        if ip in ipaddress.IPv4Network("198.18.0.0/15"):
            return False
        if ip in ipaddress.IPv4Network("0.0.0.0/8"):
            return False
        if ip in ipaddress.IPv4Network("240.0.0.0/4"):
            return False
    elif isinstance(ip, ipaddress.IPv6Address):
        if ip.is_site_local:
            return False
        if ip.ipv4_mapped and not is_safe_ip(ip.ipv4_mapped):
            return False
        if ip in ipaddress.IPv6Network("100::/64"):  # Discard prefix
            return False
        if ip in ipaddress.IPv6Network("2001:db8::/32"):  # Documentation
            return False

    return ip.is_global


def validate_url_and_resolve(url_str: str) -> None:
    try:
        parsed = urlparse(url_str)
    except Exception:
        raise HTTPException(status_code=400, detail="URL inválida.")

    if parsed.scheme.lower() not in ("http", "https"):
        raise HTTPException(
            status_code=400, detail="Esquema de URL não suportado."
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="Host não especificado.")

    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)

    try:
        addr_info = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise HTTPException(
            status_code=400, detail="Não foi possível resolver o host."
        )
    except Exception:
        raise HTTPException(
            status_code=400, detail="Erro ao validar o host de destino."
        )

    if not addr_info:
        raise HTTPException(
            status_code=400, detail="Nenhum endereço IP encontrado."
        )

    for entry in addr_info:
        sockaddr = entry[4]
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Endereço IP inválido."
            )

        if not is_safe_ip(ip_obj):
            raise HTTPException(
                status_code=403, detail="Destino restrito ou não permitido."
            )


@app.post("/webhooks/testar")
async def testar_webhook(dados: WebhookTestRequest):
    validate_url_and_resolve(dados.url)

    try:
        async with httpx.AsyncClient(
            follow_redirects=False, timeout=5.0
        ) as client:
            resposta = await client.post(dados.url, json={"evento": "teste"})
            return {"status_destino": resposta.status_code}
    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504, detail="Tempo limite de conexão esgotado."
        )
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível estabelecer conexão com o destino.",
        )