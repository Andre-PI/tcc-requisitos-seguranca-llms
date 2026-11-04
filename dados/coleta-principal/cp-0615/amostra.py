from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, Field
import httpx

app = FastAPI()


class WebhookTesteRequest(BaseModel):
    url: str = Field(..., min_length=1)


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookTesteRequest):
    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=10.0) as client:
            response = await client.post(payload.url, json={"evento": "teste"})
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Destino inacessível: {exc.__class__.__name__}") from exc

    return {"status_destino": response.status_code}