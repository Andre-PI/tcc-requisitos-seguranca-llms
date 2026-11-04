import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

app = FastAPI()


class WebhookTestRequest(BaseModel):
    url: HttpUrl


class WebhookTestResponse(BaseModel):
    status_destino: int


@app.post("/webhooks/testar", response_model=WebhookTestResponse)
async def testar_webhook(dados: WebhookTestRequest):
    payload = {"evento": "teste"}
    try:
        async with httpx.AsyncClient() as client:
            resposta = await client.post(str(dados.url), json=payload)
            return WebhookTestResponse(status_destino=resposta.status_code)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao conectar ao destino: {str(exc)}",
        )