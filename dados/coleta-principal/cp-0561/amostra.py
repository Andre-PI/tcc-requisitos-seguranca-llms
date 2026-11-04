from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import httpx

app = FastAPI()


class TestWebhookRequest(BaseModel):
    url: HttpUrl


@app.post("/webhooks/testar")
async def testar_webhook(payload: TestWebhookRequest):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(str(payload.url), json={"evento": "teste"})
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Destino indisponível") from exc

    return {"status_destino": response.status_code}