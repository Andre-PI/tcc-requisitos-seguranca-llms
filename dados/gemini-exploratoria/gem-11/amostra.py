from fastapi import FastAPI, HTTPException
import httpx
from pydantic import BaseModel

app = FastAPI()


class WebhookRequest(BaseModel):
    url: str


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookRequest):
    try:
        async with httpx.AsyncClient() as client:
            resposta = await client.post(
                payload.url,
                json={"evento": "teste"},
            )
            return {"status_destino": resposta.status_code}
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Não foi possível contatar o destino: {str(exc)}",
        )