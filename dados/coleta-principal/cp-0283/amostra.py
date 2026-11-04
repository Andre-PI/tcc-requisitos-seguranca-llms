import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

app = FastAPI()


class WebhookPayload(BaseModel):
    url: HttpUrl


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookPayload):
    target_url = str(payload.url)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(target_url, json={"evento": "teste"})
            return {"status_destino": response.status_code}
    except (httpx.RequestError, httpx.HTTPError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Não foi possível contatar o destino: {exc}",
        )