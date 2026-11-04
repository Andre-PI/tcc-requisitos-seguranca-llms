import ipaddress
import socket
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, HttpUrl
import httpx

app = FastAPI()


class WebhookRequest(BaseModel):
    url: str


def is_safe_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_multicast:
        return False
    if ip.is_private:
        return False
    if ip.is_loopback:
        return False
    if ip.is_link_local:
        return False
    if ip.is_unspecified:
        return False
    if ip.is_reserved:
        return False

    if isinstance(ip, ipaddress.IPv4Address):
        # 169.254.0.0/16 is covered by is_link_local
        # Carrier-grade NAT 100.64.0.0/10
        if ip in ipaddress.IPv4Network("100.64.0.0/10"):
            return False
        # Broadcast
        if ip == ipaddress.IPv4Address("255.255.255.255"):
            return False

    if isinstance(ip, ipaddress.IPv6Address):
        # IPv4-mapped IPv6 addresses (e.g. ::ffff:127.0.0.1)
        if ip.ipv4_mapped:
            return is_safe_ip(ip.ipv4_mapped)
        # Unique local address fc00::/7 is covered by is_private
        # Site-local (deprecated) fec0::/10
        if ip.is_site_local:
            return False

    return ip.is_global


def validate_target_url(url_str: str) -> str:
    try:
        parsed = urlparse(url_str)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="URL invalida.",
        )

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Esquema de URL nao suportado.",
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Host ausente ou invalido.",
        )

    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        addr_info = socket.getaddrinfo(
            hostname, port, type=socket.SOCK_STREAM, flags=socket.AI_CANONNAME
        )
    except socket.gaierror:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Falha na resolucao de endereco do host.",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao resolver destino.",
        )

    if not addr_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host nao resolvido.",
        )

    for item in addr_info:
        sockaddr = item[4]
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Endereco IP invalido.",
            )

        if not is_safe_ip(ip_obj):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso ao endereco de rede proibido.",
            )

    return url_str


@app.post("/webhooks/testar")
async def testar_webhook(dados: WebhookRequest):
    validated_url = validate_target_url(dados.url)

    try:
        async with httpx.AsyncClient(
            timeout=5.0,
            follow_redirects=False,
            verify=True,
        ) as client:
            resp = await client.post(
                validated_url,
                json={"evento": "teste"},
            )
            return {"status_destino": resp.status_code}
    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Tempo limite esgotado ao contatar o destino.",
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha de comunicacao com o destino.",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erro ao contatar o destino.",
        )