from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import httpx

app = FastAPI()


class TestWebhookRequest(BaseModel):
    url: HttpUrl


class TestWebhookResponse(BaseModel):
    status_destino: int


@app.post("/webhooks/testar", response_model=TestWebhookResponse)
async def testar_webhook(payload: TestWebhookRequest):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(str(payload.url), json={"evento": "teste"})
        return {"status_destino": response.status_code}
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Destino nao pode ser contatado") from exc