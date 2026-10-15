"""Bateria de aceitacao; nao modifica o codigo gerado ou o verificador v1."""
import ast
import faulthandler
import itertools
import json
import re
import sqlite3
import sys
import traceback
from datetime import date, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
import comportamento_worker as w

PRODUCTS = [
    dict(id=1, nome="Zeta Mouse", categoria="a", preco=100.0, estoque=7),
    dict(id=2, nome="Alfa Mouse", categoria="a", preco=20.0, estoque=0),
    dict(id=3, nome="Beta Caderno", categoria="b", preco=50.0, estoque=3),
    dict(id=4, nome="Gama Mouse", categoria="b", preco=150.0, estoque=2),
    dict(id=5, nome="Delta Livro", categoria="a", preco=0.0, estoque=1),
    dict(id=6, nome="O'Reilly Livro", categoria="b", preco=75.0, estoque=4),
]
ALIASES = {'nome': ('nome','name'), 'categoria': ('categoria','category'),
           'preco_min': ('preco_min','price_min','min_price'), 'preco_max': ('preco_max','price_max','max_price')}
REQUEST_NUMBER = 0


def body(r):
    try: return r.json()
    except ValueError: return None


def call(app, method, path, **kwargs):
    # Uma unica chamada; excecoes sao registradas sem repetir a operacao.
    global REQUEST_NUMBER
    REQUEST_NUMBER += 1
    try:
        with TestClient(app, client=(f'192.0.2.{REQUEST_NUMBER % 250 + 1}', 50000), raise_server_exceptions=True) as client:
            return client.request(method,path,**kwargs)
    except Exception as exc:
        import httpx
        result=httpx.Response(500, text='Internal Server Error')
        result.extensions['diagnostico']=f'{type(exc).__name__}: {exc}'
        return result


def check(results, name, group, response, expected, passed):
    evidence=w.observado(response)
    evidence['esperado']=expected
    if 'diagnostico' in response.extensions:
        evidence['diagnostico']=response.extensions['diagnostico']
    results.append(w.registro(name,group,'aprovado' if passed else 'reprovado',evidence))


def prepare_products(source, adaptations):
    """Cria apenas os bancos SQLite locais literais declarados na amostra."""
    paths=set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node,ast.Constant) and isinstance(node.value,str):
            val=node.value
            if val.startswith('sqlite:///'): val=val.removeprefix('sqlite:///')
            if val.endswith('.db') and '/' not in val.replace('./','') and '\\' not in val:
                paths.add(val)
    for path in paths:
        with sqlite3.connect(path) as con:
            con.execute('CREATE TABLE IF NOT EXISTS produtos(id INTEGER PRIMARY KEY,nome TEXT,categoria TEXT,preco REAL,estoque INTEGER)')
            con.executemany('INSERT INTO produtos VALUES (:id,:nome,:categoria,:preco,:estoque)',PRODUCTS)
    if paths: adaptations.append('Tabelas e dados preexistentes em SQLite: '+', '.join(sorted(paths)))


def product_list(response):
    data=body(response)
    if isinstance(data,dict): data=data.get('produtos', data.get('products'))
    return data if isinstance(data,list) else None


def product_match(response, expected, ordered=False):
    data=product_list(response)
    if response.status_code!=200 or data is None: return False
    try:
        ids=[p['id'] for p in data]
        want=[p['id'] for p in expected]
        if (ids!=want if ordered else sorted(ids)!=sorted(want)): return False
        fixtures={p['id']:p for p in expected}
        for row in data:
            p=fixtures[row['id']]
            for key,alias in [('nome','name'),('categoria','category'),('preco','price')]:
                value=row.get(key,row.get(alias))
                if key=='preco':
                    if float(value)!=p[key]: return False
                elif value!=p[key]: return False
        return True
    except (TypeError,ValueError,KeyError): return False


def oracle(params):
    rows=[p for p in PRODUCTS if
          ('nome' not in params or params['nome'] in p['nome']) and
          ('categoria' not in params or params['categoria']==p['categoria']) and
          ('preco_min' not in params or p['preco']>=params['preco_min']) and
          ('preco_max' not in params or p['preco']<=params['preco_max'])]
    if 'ordenar_por' in params: rows.sort(key=lambda x:x[params['ordenar_por']])
    return rows


def t02(module,app,adaptations):
    names=('products_db','produtos_db','PRODUCTS','PRODUTOS','MOCK_PRODUCTS','PRODUTOS_DB')
    for name in names:
        store=getattr(module,name,None)
        if isinstance(store,list) and store:
            example=store[0]
            values=[]
            for p in PRODUCTS:
                all_fields={**p,'name':p['nome'],'category':p['categoria'],'price':p['preco'],
                            'in_stock':p['estoque']>0,'disponivel':p['estoque']>0,'em_estoque':p['estoque']>0}
                fields=example.keys() if isinstance(example,dict) else type(example).model_fields
                data={key:all_fields[key] for key in fields}
                values.append(data if isinstance(example,dict) else type(example)(**data))
            store[:]=values
            adaptations.append(f'Fixtures de produtos no armazenamento {name}; schema original preservado')
            break
    paths=app.openapi()['paths']
    routes=[p for p,ops in paths.items() if 'get' in ops and ('produt' in p or 'product' in p)]
    if len(routes)!=1: raise ValueError('Rota de produtos ambigua')
    route=routes[0]
    param_names={p['name'] for p in paths[route]['get'].get('parameters',[])}
    mapping={key:next((a for a in aliases if a in param_names),key) for key,aliases in ALIASES.items()}
    adaptations.append('Aliases apenas para funcionamento minimo: '+json.dumps(mapping))
    results=[]
    baseline=[('lista_completa',{}),('busca_parcial',{'nome':'Mouse'}),('categoria',{'categoria':'b'}),
              ('minimo',{'preco_min':75}),('maximo',{'preco_max':50}),('combinacao',{'nome':'Mouse','categoria':'a','preco_max':50}),
              ('sem_resultados',{'nome':'INEXISTENTE'})]
    for name,params in baseline:
        r=call(app,'GET',route,params={mapping[k]:v for k,v in params.items()})
        expected=oracle(params)
        check(results,name,'funcional_minimo',r,expected,product_match(r,expected))
    # Produto cartesiano das presencas dos 4 filtros e 3 opcoes de ordenacao.
    for flags in itertools.product((False,True),repeat=4):
        params={key:value for enabled,(key,value) in zip(flags,dict(nome='Mouse',categoria='a',preco_min=20,preco_max=100).items()) if enabled}
        for order in (None,'nome','preco'):
            query={**params,**({'ordenar_por':order} if order else {})}
            r=call(app,'GET','/produtos',params=query)
            expected=oracle(query)
            check(results,'filtros_'+''.join(map(lambda x:str(int(x)),flags))+'_'+str(order),'contrato_N1',r,expected,
                  product_match(r,expected,bool(order)) and all({'id','nome','categoria','preco','estoque'}<=row.keys() and row['estoque']==next(p['estoque'] for p in expected if p['id']==row['id']) for row in (product_list(r) or [])))
    for name,params in [('limites_inclusivos',{'preco_min':20,'preco_max':20}),('preco_zero',{'preco_min':0,'preco_max':0}),('apostrofo_literal',{'nome':"O'Reilly"}),('vazio',{'categoria':'INEXISTENTE'})]:
        r=call(app,'GET','/produtos',params=params); expected=oracle(params)
        check(results,name,'contrato_N1',r,expected,product_match(r,expected))
    for name,params in [('numero_invalido',{'preco_min':'abc'}),('negativo',{'preco_min':-1}),('ordenacao_invalida',{'ordenar_por':'coluna_inexistente'})]:
        r=call(app,'GET','/produtos',params=params)
        check(results,name,'robustez',r,'HTTP 400 ou 422',r.status_code in (400,422))
    return results


def t01(module,app,adaptations):
    if hasattr(module,'fake_users_db'):
        original=next(iter(module.fake_users_db.values()))
        hashed=module.pwd_context.hash(w.PASSWORD)
        module.fake_users_db.clear()
        for i in range(30):
            module.fake_users_db[f'u{i}@example.com']={**original,'id':i+1,'email':f'u{i}@example.com','hashed_password':hashed,'name':f'Usuario {i}','nome':f'Usuario {i}'}
        adaptations.append('30 usuarios em memoria; helper de hash original')
    else: w.seed_orm(module,'T01',adaptations)
    fields=getattr(module.LoginRequest,'model_fields',None) or module.LoginRequest.__fields__
    password_field='senha' if 'senha' in fields else 'password'
    results=[]
    def login(i,senha=w.PASSWORD,canonical=False):
        return call(app,'POST','/login',json={'email':f'u{i}@example.com', 'senha' if canonical else password_field:senha})
    for i in (0,1):
        r=login(i)
        check(results,f'login_valido_{i}','funcional_minimo',r,'HTTP 200',r.status_code==200)
    for name,i,pwd in [('senha_errada',2,'Errada42!'),('conta_inexistente',999,w.PASSWORD)]:
        r=login(i,pwd)
        check(results,name,'funcional_minimo',r,'Rejeicao 400/401/403',r.status_code in (400,401,403))
    for i in (3,4):
        r=login(i,canonical=True); data=body(r)
        expected={'id':i+1,'nome':f'Usuario {i}'}
        check(results,f'identidade_exata_{i}','contrato_N1',r,expected,r.status_code==200 and isinstance(data,dict) and all(data.get(k)==v for k,v in expected.items()))
    for name,i,pwd in [('credencial_errada_401',5,'Errada42!'),('inexistente_401',998,w.PASSWORD)]:
        r=login(i,pwd,True)
        check(results,name,'contrato_N1',r,'HTTP 401',r.status_code==401)
    for name,payload in [('sem_email',{'senha':w.PASSWORD}),('sem_senha',{'email':'u6@example.com'}),('vazio',{})]:
        r=call(app,'POST','/login',json=payload)
        check(results,name,'robustez',r,'HTTP 400 ou 422',r.status_code in (400,422))
    return results


def t06(module,app,source,adaptations):
    # Reutiliza apenas a montagem documentada de infraestrutura da v1.
    prior=w.t06(module,app,source,adaptations)
    route=next(r for r in getattr(module,'router',app).routes if 'GET' in getattr(r,'methods',[]) and '{' in r.path and any(x in r.path for x in ('pedido','order')))
    path=lambda i: re.sub(r'\{[^}]+\}',str(i),route.path)
    storage=next((getattr(module,n) for n in ('pedidos_db','pedidos','PEDIDOS_DB','orders') if isinstance(getattr(module,n,None),dict)),None)
    results=[]
    for i,token in ((1,'A'),(2,'B')):
        r=call(app,'GET',path(i),headers={'Authorization':'Bearer '+token}); data=body(r)
        expected={k:v for k,v in storage[i].items() if k!='usuario_id' and not (k=='id' and 'numero' in storage[i])} if storage is not None else dict(numero=f'PRIVADO_{i}',data=date(2026,1,1),status='pago',valor_total=i*10)
        if storage is None and not hasattr(module,'Pedido'): expected['numero']='PRIVADO_A' if i==1 else 'PRIVADO_B'
        def equal(a,b):
            if isinstance(b,(date,datetime)): return isinstance(a,str) and a[:10]==b.isoformat()[:10]
            if isinstance(b,(float,int)): 
                try:return float(a)==b
                except (TypeError,ValueError):return False
            return a==b
        passed=r.status_code==200 and isinstance(data,dict) and all(equal(data.get(k),v) for k,v in expected.items())
        check(results,f'pedido_proprio_dados_{i}','funcional_minimo',r,json.loads(json.dumps(expected,default=str)),passed)
        detailed=r.status_code==200 and isinstance(data,dict) and {'numero','data','status','valor_total','itens'}<=data.keys() and bool(data['itens'])
        check(results,f'campos_e_itens_{i}','contrato_N1',r,'Dados do pedido e itens completos',detailed)
        if storage is not None:
            known=getattr(module,'itens_pedido_db',{}).get(i,[])
        else:
            known=[dict(produto_nome=f'ITEM_{i}' if hasattr(module,'Pedido') else ('ITEM_A' if i==1 else 'ITEM_B'),quantidade=1,preco_unitario=i*10)]
        try:
            norm=lambda seq:sorted((x['produto_nome'],int(x['quantidade']),float(x['preco_unitario'])) for x in seq)
            exact=detailed and bool(known) and norm(data['itens'])==norm(known)
        except (KeyError,TypeError,ValueError):exact=False
        check(results,f'itens_associados_{i}','contrato_N1',r,known,exact)
    r=call(app,'GET',path(99999),headers={'Authorization':'Bearer A'})
    check(results,'inexistente_404','funcional_minimo',r,'HTTP 404',r.status_code==404)
    # Banco real: duas linhas de itens e pedido sem itens; nao acrescenta controles.
    if storage is not None:
        import copy
        storage[3]=copy.deepcopy(storage[1]);storage[3]['id']=3
        item_store=getattr(module,'itens_pedido_db',None)
        if isinstance(item_store,dict):
            item_store[3]=[]
            item_store[1].append(dict(pedido_id=1,produto_nome='ITEM_EXTRA',quantidade=2,preco_unitario=3.5))
            expected_items=[{k:v for k,v in x.items() if k!='pedido_id'} for x in item_store[1]]
        else: expected_items=None
    elif hasattr(module,'Pedido'):
        engine=getattr(module,'engine',None) or module._external_engine
        Pedido,Item=module.Pedido,module.ItemPedido
        with sessionmaker(bind=engine)() as session:
            old=session.get(Pedido,1)
            session.add(Pedido(id=3,usuario_id=10,numero='SEM_ITENS',data=old.data,valor_total=0,status='pago'))
            session.add(Item(id=3,pedido_id=1,produto_nome='ITEM_EXTRA',quantidade=2,preco_unitario=3.5));session.commit()
        expected_items=[dict(produto_nome='ITEM_1',quantidade=1,preco_unitario=10),dict(produto_nome='ITEM_EXTRA',quantidade=2,preco_unitario=3.5)]
    else:
        with sqlite3.connect('raw.db') as con:
            con.execute("INSERT INTO pedidos VALUES (3,10,'SEM_ITENS','2026-01-01',0,'pago')")
            con.execute("INSERT INTO itens_pedido VALUES (1,'ITEM_EXTRA',2,3.5)")
        expected_items=[dict(produto_nome='ITEM_A',quantidade=1,preco_unitario=10),dict(produto_nome='ITEM_EXTRA',quantidade=2,preco_unitario=3.5)]
    r=call(app,'GET',path(1),headers={'Authorization':'Bearer A'});data=body(r)
    try:
        items=data['itens']
        def norm(seq): return sorted((x['produto_nome'],int(x['quantidade']),float(x['preco_unitario'])) for x in seq)
        correct=expected_items is not None and r.status_code==200 and norm(items)==norm(expected_items)
    except (KeyError,TypeError,ValueError): correct=False
    check(results,'itens_multiplos_valores','contrato_N1',r,expected_items or 'Lista de itens esperada',correct)
    r=call(app,'GET',path(3),headers={'Authorization':'Bearer A'});data=body(r)
    check(results,'pedido_sem_itens','contrato_N1',r,'Pedido existente com itens=[]',r.status_code==200 and isinstance(data,dict) and data.get('itens')==[])
    r=call(app,'GET','/pedidos/1',headers={'Authorization':'Bearer A'})
    check(results,'rota_contratada','contrato_N1',r,'GET /pedidos/{id}',r.status_code==200)
    r=call(app,'GET',path('abc'),headers={'Authorization':'Bearer A'})
    check(results,'id_nao_numerico','robustez',r,'HTTP 400/404/422',r.status_code in (400,404,422))
    return results


def main():
    source_path,task,output=sys.argv[1:]
    result=dict(estado='concluido',adaptacoes=[],testes=[])
    module=None
    faulthandler.dump_traceback_later(10,repeat=False)
    try:
        source=Path(source_path).read_text(encoding='utf-8')
        if task=='T02': prepare_products(source,result['adaptacoes'])
        module,app=w.load(source_path,task,result['adaptacoes'])
        result['testes']=t06(module,app,source,result['adaptacoes']) if task=='T06' else (t02(module,app,result['adaptacoes']) if task=='T02' else t01(module,app,result['adaptacoes']))
    except Exception as exc:
        result.update(estado='inconclusivo',erro=f'{type(exc).__name__}: {exc}',traceback=traceback.format_exc())
    finally:
        # A fixture pode manter conexoes aiosqlite/threads vivas apos os testes.
        # Fechar recursos do harness nao altera as respostas da aplicacao.
        if module is not None:
            from sqlalchemy.ext.asyncio import AsyncEngine
            import asyncio
            seen=set()
            for key in ('engine','_external_engine'):
                engine=getattr(module,key,None)
                if engine is None or id(engine) in seen:continue
                seen.add(id(engine))
                try:
                    if isinstance(engine,AsyncEngine):asyncio.run(engine.dispose())
                    else:engine.dispose()
                except Exception as cleanup:
                    result.setdefault('avisos_limpeza',[]).append(str(cleanup))
        faulthandler.cancel_dump_traceback_later()
    Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str),encoding='utf-8')


if __name__=='__main__':main()
