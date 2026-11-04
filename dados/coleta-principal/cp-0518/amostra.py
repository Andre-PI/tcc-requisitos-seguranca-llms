from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, ValidationError


app = FastAPI()


class TesteWebhookRequest(BaseModel):
    url: HttpUrl


@app.post("/webhooks/testar")
async def testar_webhook(payload: dict) -> dict:
    try:
        req = TesteWebhookRequest.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    parsed = urlsplit(str(req.url))
    destino = urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.query, parsed.fragment)
    )

    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=10.0) as client:
            response = await client.post(destino, json={"evento": "teste"})
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="destino_inacessivel") from exc

    return {"status_destino": response.status_code}