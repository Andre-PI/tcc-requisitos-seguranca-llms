from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, ValidationError


app = FastAPI()


class WebhookTesteRequest(BaseModel):
    url: HttpUrl


class WebhookTesteResponse(BaseModel):
    status_destino: int


@app.post("/webhooks/testar", response_model=WebhookTesteResponse)
async def testar_webhook(payload: dict[str, Any]) -> WebhookTesteResponse:
    try:
        req = WebhookTesteRequest.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(str(req.url), json={"evento": "teste"})
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Destino indisponível") from exc

    return WebhookTesteResponse(status_destino=response.status_code)