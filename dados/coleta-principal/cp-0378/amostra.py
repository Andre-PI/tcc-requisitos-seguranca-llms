from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, HttpUrl
import httpx

app = FastAPI()


class WebhookTestRequest(BaseModel):
    url: HttpUrl


class WebhookTestResponse(BaseModel):
    status_destino: int


@app.post("/webhooks/testar", response_model=WebhookTestResponse)
async def testar_webhook(dados: WebhookTestRequest):
    payload = {"evento": "teste"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(str(dados.url), json=payload)
            return WebhookTestResponse(status_destino=response.status_code)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao contatar o destino: {str(exc)}",
        )