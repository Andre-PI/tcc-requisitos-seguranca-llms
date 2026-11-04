import ipaddress
import socket
from urllib.parse import urlparse, urlunparse

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, AnyHttpUrl, ValidationError

app = FastAPI()


class WebhookTestRequest(BaseModel):
    url: AnyHttpUrl


def _is_public_ip(ip: ipaddress._BaseAddress) -> bool:
    if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
        return False
    if ip.version == 6 and ip.ipv4_mapped is not None:
        return False
    # Reject other non-public special-use ranges
    if getattr(ip, "is_reserved", False):
        return False
    if getattr(ip, "is_site_local", False):
        return False
    return True


def _validate_destination(url: str) -> str:
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=422, detail="URL inválida")

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="URL deve usar http ou https")

    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="URL deve conter host")

    host = parsed.hostname

    # Reject raw IPs and alternative encodings by resolving and validating all results.
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Host inválido ou não resolvível")
    except Exception:
        raise HTTPException(status_code=400, detail="Host inválido ou não resolvível")

    if not infos:
        raise HTTPException(status_code=400, detail="Host inválido ou não resolvível")

    resolved_ips = set()
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Host inválido ou não resolvível")
        resolved_ips.add(ip_obj)

    if not resolved_ips:
        raise HTTPException(status_code=400, detail="Host inválido ou não resolvível")

    for ip in resolved_ips:
        if not _is_public_ip(ip):
            raise HTTPException(status_code=403, detail="Destino não permitido")

    # Preserve path and query exactly, but normalize the URL from parsed components.
    normalized = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path or "",
            parsed.params or "",
            parsed.query or "",
            parsed.fragment or "",
        )
    )
    return normalized


@app.post("/webhooks/testar")
def testar_webhook(payload: dict):
    try:
        req = WebhookTestRequest.model_validate(payload)
    except ValidationError:
        raise HTTPException(status_code=422, detail="JSON inválido")

    target_url = _validate_destination(str(req.url))

    try:
        with httpx.Client(follow_redirects=False, timeout=httpx.Timeout(5.0)) as client:
            resp = client.post(target_url, json={"evento": "teste"})
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteError, httpx.RemoteProtocolError, httpx.NetworkError):
        raise HTTPException(status_code=502, detail="Falha ao contatar o destino")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Falha ao contatar o destino")
    except Exception:
        raise HTTPException(status_code=502, detail="Falha ao contatar o destino")

    return {"status_destino": resp.status_code}