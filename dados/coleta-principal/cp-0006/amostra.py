from fastapi import FastAPI, HTTPException
import httpx
from pydantic import BaseModel, HttpUrl

app = FastAPI()


class WebhookTestRequest(BaseModel):
    url: HttpUrl


class WebhookTestResponse(BaseModel):
    status_destino: int


@app.post("/webhooks/testar", response_model=WebhookTestResponse)
async def testar_webhook(dados: WebhookTestRequest):
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resposta = await client.post(
                str(dados.url),
                json={"evento": "teste"},
            )
            return WebhookTestResponse(status_destino=resposta.status_code)
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Falha ao contatar a URL de destino: {str(exc)}",
            )