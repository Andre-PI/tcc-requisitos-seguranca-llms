from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI()


class WebhookRequest(BaseModel):
    url: str


@app.post("/webhooks/testar")
async def testar_webhook(dados: WebhookRequest):
    payload = {"evento": "teste"}
    try:
        async with httpx.AsyncClient() as client:
            resposta = await client.post(dados.url, json=payload)
            return {"status_destino": resposta.status_code}
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Não foi possível contatar o destino: {str(exc)}",
        )