import ipaddress
import socket
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, HttpUrl
import httpx

app = FastAPI()


class WebhookRequest(BaseModel):
    url: HttpUrl


def is_safe_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

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

    # Metadata service protection (e.g. AWS 169.254.169.254)
    if isinstance(ip, ipaddress.IPv4Address):
        if ip in ipaddress.IPv4Network("169.254.0.0/16"):
            return False
        if ip in ipaddress.IPv4Network("100.64.0.0/10"):
            return False
        if ip in ipaddress.IPv4Network("192.0.0.0/24"):
            return False
        if ip in ipaddress.IPv4Network("198.18.0.0/15"):
            return False

    # IPv6 checks
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped:
            return is_safe_ip(str(ip.ipv4_mapped))
        if ip in ipaddress.IPv6Network("fc00::/7"):
            return False
        if ip in ipaddress.IPv6Network("fe80::/10"):
            return False
        if ip in ipaddress.IPv6Network("::ffff:0:0/96"):
            return False

    return True


def validate_target_url(raw_url: str):
    parsed = urlparse(raw_url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL com esquema invalido.",
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL sem host valido.",
        )

    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        addr_info = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nao foi possivel resolver o host informado.",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host invalido.",
        )

    if not addr_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host nao resolveu nenhum endereco.",
        )

    for entry in addr_info:
        ip_addr = entry[4][0]
        if not is_safe_ip(ip_addr):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Destino nao permitido.",
            )


@app.post("/webhooks/testar")
async def testar_webhook(dados: WebhookRequest):
    url_str = str(dados.url)
    validate_target_url(url_str)

    try:
        async with httpx.AsyncClient(
            timeout=5.0,
            follow_redirects=False,
        ) as client:
            resposta = await client.post(
                url_str,
                json={"evento": "teste"},
            )
            return {"status_destino": resposta.status_code}
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao contatar o destino.",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao contatar o destino.",
        )