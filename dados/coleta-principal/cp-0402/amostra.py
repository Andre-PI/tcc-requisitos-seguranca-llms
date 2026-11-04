from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import httpx

app = FastAPI()


class WebhookTestRequest(BaseModel):
    url: HttpUrl


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookTestRequest):
    try:
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.post(
                str(payload.url),
                json={"evento": "teste"},
                timeout=10.0,
            )
        return {"status_destino": response.status_code}
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Destino indisponível") from exc