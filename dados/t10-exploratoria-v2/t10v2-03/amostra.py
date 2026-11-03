from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import httpx

app = FastAPI()

class WebhookRequest(BaseModel):
    url: HttpUrl

@app.post("/webhooks/testar")
async def testar_webhook(req: WebhookRequest):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(req.url, json={"evento": "teste"})
            return {"status_destino": resp.status_code}
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Não foi possível contatar o destino")