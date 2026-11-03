from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import httpx

app = FastAPI()


class WebhookRequest(BaseModel):
    url: HttpUrl


@app.post("/webhooks/testar")
async def testar_webhook(req: WebhookRequest):
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            response = await client.post(req.url, json={"evento": "teste"})
        return {"status_destino": response.status_code}
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Destino inacessível")