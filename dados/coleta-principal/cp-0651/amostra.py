from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI()


class WebhookTestRequest(BaseModel):
    url: str


@app.post("/webhooks/testar")
async def testar_webhook(dados: WebhookTestRequest):
    try:
        async with httpx.AsyncClient() as client:
            resposta = await client.post(dados.url, json={"evento": "teste"})
            return {"status_destino": resposta.status_code}
    except (httpx.RequestError, ValueError):
        raise HTTPException(status_code=502, detail="Erro ao contatar o destino.")