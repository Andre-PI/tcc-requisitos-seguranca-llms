from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import httpx

app = FastAPI()


class WebhookTesteRequest(BaseModel):
    url: HttpUrl


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookTesteRequest):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(str(payload.url), json={"evento": "teste"})
        return {"status_destino": response.status_code}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Destino indisponível") from exc