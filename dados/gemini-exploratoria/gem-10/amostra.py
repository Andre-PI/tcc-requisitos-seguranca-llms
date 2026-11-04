from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import httpx

app = FastAPI()


class WebhookTestRequest(BaseModel):
    url: str


class WebhookTestResponse(BaseModel):
    status_destino: int


@app.post(
    "/webhooks/testar",
    response_model=WebhookTestResponse,
    status_code=status.HTTP_200_OK,
)
async def testar_webhook(dados: WebhookTestRequest):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resposta = await client.post(dados.url, json={"evento": "teste"})
            return {"status_destino": resposta.status_code}
    except (httpx.RequestError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao contatar a URL de destino: {str(exc)}",
        )