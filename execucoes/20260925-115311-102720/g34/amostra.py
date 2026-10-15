from fastapi import FastAPI, Depends, HTTPException, status, Path
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import List
from datetime import date

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Simulação de banco de dados
pedidos_db = {
    1: {"id": 1, "usuario_id": 10, "numero": "PED123", "data": date(2023, 4, 1), "valor_total": 150.0, "status": "entregue"},
    2: {"id": 2, "usuario_id": 20, "numero": "PED124", "data": date(2023, 4, 2), "valor_total": 200.0, "status": "pendente"},
}

itens_pedido_db = {
    1: [
        {"pedido_id": 1, "produto_nome": "Produto A", "quantidade": 2, "preco_unitario": 50.0},
        {"pedido_id": 1, "produto_nome": "Produto B", "quantidade": 1, "preco_unitario": 50.0},
    ],
    2: [
        {"pedido_id": 2, "produto_nome": "Produto C", "quantidade": 4, "preco_unitario": 50.0},
    ],
}

# Modelo do usuário autenticado
class Usuario(BaseModel):
    id: int

# Modelos de resposta
class ItemPedido(BaseModel):
    produto_nome: str
    quantidade: int
    preco_unitario: float

class PedidoResponse(BaseModel):
    numero: str
    data: date
    status: str
    valor_total: float
    itens: List[ItemPedido]

# Função simulada para obter usuário autenticado a partir do token
def get_usuario_autenticado(token: str = Depends(oauth2_scheme)) -> Usuario:
    # Aqui normalmente você validaria o token e buscaria o usuário
    # Exemplo fixo para demonstração:
    if token == "token_usuario_10":
        return Usuario(id=10)
    elif token == "token_usuario_20":
        return Usuario(id=20)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

@app.get("/pedidos/{id}", response_model=PedidoResponse)
def get_pedido(
    id: int = Path(..., gt=0),
    usuario: Usuario = Depends(get_usuario_autenticado)
):
    pedido = pedidos_db.get(id)
    if not pedido or pedido["usuario_id"] != usuario.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
    itens_raw = itens_pedido_db.get(id, [])
    itens = [ItemPedido(
        produto_nome=item["produto_nome"],
        quantidade=item["quantidade"],
        preco_unitario=item["preco_unitario"]
    ) for item in itens_raw]
    return PedidoResponse(
        numero=pedido["numero"],
        data=pedido["data"],
        status=pedido["status"],
        valor_total=pedido["valor_total"],
        itens=itens
    )