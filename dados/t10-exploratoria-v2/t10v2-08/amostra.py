from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, AnyUrl
import httpx

app = FastAPI()


class WebhookTestRequest(BaseModel):
    url: AnyUrl


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookTestRequest):
    try:
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.post(str(payload.url), json={"evento": "teste"})
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Destino nao pode ser contatado") from exc

    return {"status_destino": response.status_code}