import ipaddress
import socket
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, HttpUrl
import httpx

app = FastAPI()

class WebhookRequest(BaseModel):
    url: HttpUrl

def is_forbidden_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_multicast:
        return True
    if ip.is_private:
        return True
    if ip.is_loopback:
        return True
    if ip.is_link_local:
        return True
    if ip.is_unspecified:
        return True
    if ip.is_reserved:
        return True
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.is_site_local:
            return True
        if ip.ipv4_mapped:
            return is_forbidden_ip(ip.ipv4_mapped)
    if isinstance(ip, ipaddress.IPv4Address):
        # 169.254.0.0/16 is link_local, but check cloud metadata 169.254.169.254 explicitly
        if ip in ipaddress.ip_network("169.254.0.0/16"):
            return True
        if ip in ipaddress.ip_network("100.64.0.0/10"):
            return True
        if ip in ipaddress.ip_network("192.0.0.0/24"):
            return True
        if ip in ipaddress.ip_network("198.18.0.0/15"):
            return True
        if ip in ipaddress.ip_network("0.0.0.0/8"):
            return True
    return False

def validate_url(target_url: str):
    parsed = urlparse(target_url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esquema de URL inválido. Apenas http e https são permitidos."
        )
    
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL não possui um host válido."
        )

    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        addr_info = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível resolver o host informado."
        )

    if not addr_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum endereço encontrado para o host informado."
        )

    for entry in addr_info:
        ip_str = entry[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Endereço IP inválido ou não permitido."
            )
        if is_forbidden_ip(ip):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Destino não permitido."
            )

@app.post("/webhooks/testar")
async def testar_webhook(dados: WebhookRequest):
    url_str = str(dados.url)
    validate_url(url_str)

    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
            resposta = await client.post(
                url_str,
                json={"evento": "teste"}
            )
            return {"status_destino": resposta.status_code}
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao contatar o destino."
        )