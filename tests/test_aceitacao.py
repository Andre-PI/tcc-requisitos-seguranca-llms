import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from pydantic import BaseModel
from aceitacao_worker import PRODUCTS, oracle, product_match, t02
import httpx


def test_oraculo_limites_ordenacao_e_combinacao():
    assert [p['id'] for p in oracle(dict(nome='Mouse',categoria='a',preco_min=20,preco_max=100,ordenar_por='preco'))]==[2,1]
    assert [p['id'] for p in oracle(dict(preco_min=20,preco_max=20))]==[2]
    assert [p['id'] for p in oracle(dict(preco_min=0,preco_max=0))]==[5]
    assert [p['id'] for p in oracle(dict(nome="O'Reilly"))]==[6]


def test_status_200_nao_basta():
    assert not product_match(httpx.Response(200,json=[]),PRODUCTS)
    wrong=[dict(p) for p in PRODUCTS];wrong[0]['preco']=999
    assert not product_match(httpx.Response(200,json=wrong),PRODUCTS)
    assert not product_match(httpx.Response(200,json=list(reversed(PRODUCTS))),PRODUCTS,True)


def product_app(broken=False):
    app=FastAPI()
    @app.get('/produtos')
    def products(nome:str|None=None,categoria:str|None=None,preco_min:float|None=None,preco_max:float|None=None,ordenar_por:str|None=None):
        from fastapi import HTTPException
        if ordenar_por not in (None,'nome','preco') or (preco_min is not None and preco_min<0):raise HTTPException(422)
        rows=[dict(p) for p in PRODUCTS]
        if nome:rows=[p for p in rows if nome in p['nome']]
        if categoria and not broken:rows=[p for p in rows if p['categoria']==categoria]
        if preco_min is not None:rows=[p for p in rows if p['preco']>=preco_min]
        if preco_max is not None:rows=[p for p in rows if p['preco']<=preco_max]
        if ordenar_por:rows.sort(key=lambda p:p[ordenar_por])
        return rows
    return app


def test_bateria_aceita_controle_e_rejeita_filtro_ignorado():
    good=t02(SimpleNamespace(),product_app(),[])
    assert len(good)==62
    assert all(t['status']=='aprovado' for t in good)
    bad=t02(SimpleNamespace(),product_app(True),[])
    assert any(t['tipo']=='contrato_N1' and t['status']=='reprovado' for t in bad)


def test_fixtures_preexistentes_incluem_reflexao(tmp_path,monkeypatch):
    import sqlite3
    from aceitacao_worker import prepare_products
    monkeypatch.chdir(tmp_path)
    prepare_products("DATABASE_URL='sqlite:///./test.db'",[])
    with sqlite3.connect('test.db') as con:
        assert con.execute('SELECT count(*) FROM produtos').fetchone()[0]==6


def test_login_confere_identidade_e_nao_esgota_limite_por_ip():
    from fastapi import HTTPException,Request
    from aceitacao_worker import t01
    from comportamento_worker import PASSWORD
    for wrong_identity in (False,True):
        class LoginRequest(BaseModel):
            email:str
            senha:str
        module=SimpleNamespace(LoginRequest=LoginRequest,fake_users_db={'original':{}},pwd_context=SimpleNamespace(hash=lambda value:value))
        app=FastAPI();ips={}
        @app.post('/login')
        def login(payload:LoginRequest,request:Request):
            ip=request.client.host;ips[ip]=ips.get(ip,0)+1
            if ips[ip]>5:raise HTTPException(429)
            user=module.fake_users_db.get(payload.email)
            if user is None or payload.senha!=PASSWORD:raise HTTPException(401)
            return dict(id=999 if wrong_identity else user['id'],nome=user['nome'])
        r=t01(module,app,[])
        assert all(t['status']=='aprovado' for t in r if t['tipo']=='funcional_minimo')
        identities=[t for t in r if t['teste'].startswith('identidade_exata')]
        assert all(t['status']==('reprovado' if wrong_identity else 'aprovado') for t in identities)
        assert max(ips.values())==1


def test_pedidos_confere_itens_e_pedido_sem_itens():
    from fastapi import Depends,HTTPException
    from aceitacao_worker import t06
    for wrong_items in (False,True):
        app=FastAPI()
        module=SimpleNamespace(pedidos_db={i:dict(id=i,usuario_id=i*10,numero=f'P{i}',data='2026-01-01',status='pago',valor_total=i*10) for i in (1,2)},
                               itens_pedido_db={i:[dict(pedido_id=i,produto_nome=f'ITEM_{i}',quantidade=1,preco_unitario=i*10)] for i in (1,2)})
        def get_current_user():raise NotImplementedError
        @app.get('/pedidos/{id}')
        def get(id:int,user=Depends(get_current_user)):
            p=module.pedidos_db.get(id)
            if not p or p['usuario_id']!=user.id:raise HTTPException(404)
            items=[{k:v for k,v in item.items() if k!='pedido_id'} for item in module.itens_pedido_db.get(id,[])]
            if wrong_items:
                for item in items:item['quantidade']=999
            return {**{k:v for k,v in p.items() if k not in ('id','usuario_id')},'itens':items}
        r=t06(module,app,'',[])
        assert all(t['status']=='aprovado' for t in r if t['tipo']=='funcional_minimo')
        item_cases=[t for t in r if t['teste'].startswith('itens_')]
        assert all(t['status']==('reprovado' if wrong_items else 'aprovado') for t in item_cases)
        assert next(t for t in r if t['teste']=='pedido_sem_itens')['status']=='aprovado'
