from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import httpx

app = FastAPI()


class WebhookPayload(BaseModel):
    url: HttpUrl


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookPayload):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                str(payload.url),
                json={"evento": "teste"},
            )
            return {"status_destino": response.status_code}
    except (httpx.RequestError, Exception) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao contatar a URL de destino: {str(exc)}",
        )