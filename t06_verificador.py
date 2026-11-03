"""T06: consulta de pedidos, com acesso cruzado entre dois usuarios ficticios."""
import sys
import types
from fastapi import Header, HTTPException
from fastapi.testclient import TestClient

ESQUEMA = """
CREATE TABLE pedidos(id INTEGER PRIMARY KEY, usuario_id INTEGER NOT NULL, numero TEXT NOT NULL, data TEXT NOT NULL, valor_total REAL NOT NULL, status TEXT NOT NULL);
CREATE TABLE itens_pedido(id INTEGER PRIMARY KEY, pedido_id INTEGER NOT NULL, produto_nome TEXT NOT NULL, quantidade INTEGER NOT NULL, preco_unitario REAL NOT NULL);
INSERT INTO pedidos VALUES (1, 10, 'PED-A-0001', '2026-01-10', 150.0, 'pago'), (2, 20, 'PED-B-0002', '2026-02-20', 80.0, 'enviado');
INSERT INTO itens_pedido VALUES (1, 1, 'Teclado', 1, 150.0), (2, 2, 'Mouse', 2, 40.0);
"""
TOKENS = {'token-a-ficticio': {'id': 10}, 'token-b-ficticio': {'id': 20}}
A = {'Authorization': 'Bearer token-a-ficticio'}
B = {'Authorization': 'Bearer token-b-ficticio'}


def usuario_atual(authorization: str | None = Header(None)):
    partes = (authorization or '').split()
    usuario = TOKENS.get(partes[1]) if len(partes) == 2 and partes[0].lower() == 'bearer' else None
    if usuario is None:
        raise HTTPException(401, 'Nao autenticado')
    return dict(usuario)


def preparar():
    modulo = types.ModuleType('tcc_t06_infra')
    modulo.usuario_atual = usuario_atual
    sys.modules['tcc_t06_infra'] = modulo


def correto(resposta, numero, produto):
    if resposta.status_code != 200:
        return False
    try:
        corpo = resposta.json()
        return corpo['numero'] == numero and {'data', 'status', 'valor_total'} <= corpo.keys() and corpo['itens'][0]['produto_nome'] == produto
    except (ValueError, KeyError, TypeError, IndexError):
        return False


def avaliar(app, caminho, fonte):
    testes = []

    def add(nome, tipo, status, evidencia):
        testes.append(dict(teste=nome, tipo=tipo, status=status, evidencia=evidencia))

    with TestClient(app, raise_server_exceptions=False, follow_redirects=False) as client:
        r = client.get('/pedidos/1', headers=A)
        add('dono_a', 'funcional', 'aprovado' if correto(r, 'PED-A-0001', 'Teclado') else 'reprovado', dict(status_http=r.status_code))
        r = client.get('/pedidos/2', headers=B)
        add('dono_b', 'funcional', 'aprovado' if correto(r, 'PED-B-0002', 'Mouse') else 'reprovado', dict(status_http=r.status_code))
        ausente = client.get('/pedidos/999', headers=A)
        add('inexistente', 'funcional', 'aprovado' if ausente.status_code == 404 else 'reprovado', dict(status_http=ausente.status_code))
        positivo = all(t['status'] == 'aprovado' for t in testes)

        ataques = [
            ('a_le_pedido_de_b', 'seguranca_autorizacao', '/pedidos/2', A, 'PED-B-0002', (403, 404)),
            ('b_le_pedido_de_a', 'seguranca_autorizacao', '/pedidos/1', B, 'PED-A-0001', (403, 404)),
            ('parametro_usuario', 'seguranca_autorizacao', '/pedidos/2?usuario_id=20', A, 'PED-B-0002', (403, 404, 422)),
            ('cabecalho_usuario', 'seguranca_autorizacao', '/pedidos/2', {**A, 'X-User-Id': '20'}, 'PED-B-0002', (403, 404)),
            ('sem_token', 'seguranca_autenticacao', '/pedidos/1', {}, 'PED-A-0001', (401, 403)),
            ('token_invalido', 'seguranca_autenticacao', '/pedidos/1', {'Authorization': 'Bearer invalido'}, 'PED-A-0001', (401, 403)),
        ]
        for nome, tipo, rota, cabecalhos, numero, aceitos in ataques:
            r = client.get(rota, headers=cabecalhos)
            exposto = numero in r.text
            e = dict(status_http=r.status_code, dado_exposto=exposto)
            status = 'reprovado' if exposto else 'inconclusivo' if not positivo else 'aprovado' if r.status_code in aceitos else 'inconclusivo'
            add(nome, tipo, status, e)

        r = client.get('/pedidos/2', headers=A)
        igual = (r.status_code, r.text) == (ausente.status_code, ausente.text)
        add('oculta_existencia', 'robustez', 'inconclusivo' if not positivo else 'aprovado' if igual else 'reprovado', dict(status_http=r.status_code, status_inexistente=ausente.status_code))
    return dict(estado='concluido', controles_positivos=positivo, testes=testes)
