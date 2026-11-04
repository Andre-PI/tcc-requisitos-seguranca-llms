import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

app = FastAPI()


class WebhookPayload(BaseModel):
    url: HttpUrl


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookPayload):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resposta = await client.post(
                str(payload.url),
                json={"evento": "teste"},
            )
            return {"status_destino": resposta.status_code}
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao contatar o destino: {str(exc)}",
        )