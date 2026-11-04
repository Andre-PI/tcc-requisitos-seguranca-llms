from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import httpx

app = FastAPI()


class WebhookTesteRequest(BaseModel):
    url: HttpUrl


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookTesteRequest):
    destino = str(payload.url)
    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=10.0) as client:
            resposta = await client.post(destino, json={"evento": "teste"})
    except (httpx.RequestError, httpx.TimeoutException) as exc:
        raise HTTPException(status_code=502, detail="Destino indisponível") from exc

    return {"status_destino": resposta.status_code}