import ipaddress
import socket
from urllib.parse import urlparse
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

app = FastAPI()

class WebhookRequest(BaseModel):
    url: HttpUrl

def validate_and_resolve_host(hostname: str, port: int) -> list[str]:
    try:
        addr_info = socket.getaddrinfo(hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except (socket.gaierror, socket.herror, OSError):
        raise HTTPException(status_code=400, detail="Destino invalido.")

    if not addr_info:
        raise HTTPException(status_code=400, detail="Destino invalido.")

    resolved_ips = set()
    for item in addr_info:
        sockaddr = item[4]
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Destino invalido.")

        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            raise HTTPException(status_code=403, detail="Destino restrito.")

        if isinstance(ip, ipaddress.IPv4Address):
            if ip in ipaddress.ip_network("169.254.0.0/16") or ip in ipaddress.ip_network("100.64.0.0/10") or ip in ipaddress.ip_network("0.0.0.0/8"):
                raise HTTPException(status_code=403, detail="Destino restrito.")

        if isinstance(ip, ipaddress.IPv6Address):
            if ip.ipv4_mapped:
                mapped_ip = ip.ipv4_mapped
                if mapped_ip.is_loopback or mapped_ip.is_private or mapped_ip.is_link_local or mapped_ip.is_reserved or mapped_ip.is_unspecified:
                    raise HTTPException(status_code=403, detail="Destino restrito.")
                if mapped_ip in ipaddress.ip_network("169.254.0.0/16") or mapped_ip in ipaddress.ip_network("100.64.0.0/10") or mapped_ip in ipaddress.ip_network("0.0.0.0/8"):
                    raise HTTPException(status_code=403, detail="Destino restrito.")

        resolved_ips.add(ip_str)

    return list(resolved_ips)

@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookRequest):
    raw_url = str(payload.url)
    parsed = urlparse(raw_url)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(status_code=400, detail="URL invalida.")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    validate_and_resolve_host(parsed.hostname, port)

    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
            response = await client.post(raw_url, json={"evento": "teste"})
            return {"status_destino": response.status_code}
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Falha ao contatar o destino.")
    except Exception:
        raise HTTPException(status_code=502, detail="Falha ao contatar o destino.")