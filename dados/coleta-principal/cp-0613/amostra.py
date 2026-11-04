import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

app = FastAPI()


class WebhookTestRequest(BaseModel):
    url: HttpUrl


class WebhookTestResponse(BaseModel):
    status_destino: int


@app.post("/webhooks/testar", response_model=WebhookTestResponse, status_code=200)
async def testar_webhook(payload: WebhookTestRequest):
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
            detail=f"Falha ao conectar com o destino: {str(exc)}",
        )