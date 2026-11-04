from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import httpx

app = FastAPI()


class WebhookPayload(BaseModel):
    url: HttpUrl


class WebhookResponse(BaseModel):
    status_destino: int


@app.post("/webhooks/testar", response_model=WebhookResponse)
async def testar_webhook(payload: WebhookPayload):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resposta = await client.post(
                str(payload.url),
                json={"evento": "teste"},
            )
            return {"status_destino": resposta.status_code}
    except (httpx.RequestError, Exception):
        raise HTTPException(
            status_code=502,
            detail="Nao foi possivel contatar a URL de destino informada.",
        )