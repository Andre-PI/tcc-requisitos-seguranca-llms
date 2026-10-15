import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel
from comportamento_worker import t06, t01, PASSWORD


def fixture_app(mode):
    app = FastAPI()
    pedidos = {1:{'id':1,'usuario_id':10},2:{'id':2,'usuario_id':20}}
    def get_current_user():
        raise NotImplementedError
    @app.get('/pedidos/{id}')
    def get(id: int, user=Depends(get_current_user)):
        if mode=='broken': raise RuntimeError('falha funcional')
        if id not in pedidos: raise HTTPException(404,'inexistente')
        if mode=='secure' and pedidos[id]['usuario_id']!=user.id:
            raise HTTPException(404,'inexistente')
        if mode=='deny_all': raise HTTPException(404,'inexistente')
        return pedidos[id]
    return SimpleNamespace(pedidos=pedidos), app


def test_idor_vulneravel_e_detectado():
    module, app = fixture_app('vulnerable')
    r=t06(module,app,'',[])
    assert sum(t['status']=='vulneravel' for t in r)==2


def test_controle_seguro():
    module, app = fixture_app('secure')
    r=t06(module,app,'',[])
    assert all(t['status']=='aprovado' for t in r if t['teste'].startswith('idor'))
    assert next(t for t in r if t['teste']=='sem_token')['tipo']=='contrato_auth'


def test_falha_funcional_nao_e_seguranca():
    for mode in ('broken','deny_all'):
        module, app = fixture_app(mode)
        r=t06(module,app,'',[])
        assert all(t['status']=='inconclusivo' for t in r if t['teste'].startswith('idor'))


def rate_app(mode):
    app = FastAPI()
    class LoginRequest(BaseModel):
        email: str
        senha: str
    counts_ip, counts_user = {}, {}
    @app.post('/login')
    def login(data: LoginRequest, request: Request):
        ip = request.client.host
        counts_ip[ip] = counts_ip.get(ip,0)+1
        counts_user[data.email] = counts_user.get(data.email,0)+1
        if mode in ('ip','both') and counts_ip[ip]>4:
            raise HTTPException(401,'invalido')
        if mode=='both' and counts_user[data.email]>4:
            raise HTTPException(401,'invalido')
        if data.senha != PASSWORD or data.email=='u9999@example.com':
            raise HTTPException(401,'invalido')
        return {'id':1,'nome':'teste'}
    module = SimpleNamespace(LoginRequest=LoginRequest, fake_users_db={'x':{}}, pwd_context=SimpleNamespace(hash=lambda x:x))
    return module,app


def test_rate_limit_401_e_dimensoes_separadas():
    for mode, expected in [('none',('vulneravel','vulneravel')),('ip',('vulneravel','aprovado')),('both',('aprovado','aprovado'))]:
        module,app=rate_app(mode)
        results=t01(module,app,[],6)
        rates={r['teste']:r['status'] for r in results}
        assert (rates['limite_conta'],rates['limite_ip'])==expected


def test_rota_orders_e_armazenamento_maiusculo():
    for name,path in [('orders','/orders/{id}'),('PEDIDOS_DB','/pedidos/{id}')]:
        app=FastAPI()
        storage={1:{'id':1},2:{'id':2}}
        @app.get(path)
        def get(id:int):
            if id not in storage:raise HTTPException(404,'inexistente')
            return storage[id]
        r=t06(SimpleNamespace(**{name:storage}),app,'',[])
        assert next(t for t in r if t['teste']=='sem_token')['status']=='vulneravel'
