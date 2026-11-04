from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI()


class WebhookPayload(BaseModel):
    url: str


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookPayload):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                payload.url,
                json={"evento": "teste"},
            )
            return {"status_destino": response.status_code}
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Não foi possível contatar o destino: {str(exc)}",
        )