"""Referencias T06: aplicacoes corretas e falhas conhecidas para validar o verificador."""
import os
import sqlite3
from fastapi import Depends, FastAPI, Header, HTTPException
from t06_verificador import usuario_atual

MODOS = ('protegida', 'sem_dono', 'sem_autenticacao', 'dono_por_parametro', 'dono_por_cabecalho', 'token_opcional', 'responde_403', 'mensagem_diferente', 'nega_tudo', 'finge_sucesso')


def fonte(modo):
    return ''


def buscar(identificador):
    con = sqlite3.connect(os.environ['TCC_DB_PATH'])
    con.row_factory = sqlite3.Row
    try:
        pedido = con.execute('SELECT * FROM pedidos WHERE id=?', (identificador,)).fetchone()
        if pedido is None:
            return None
        itens = con.execute('SELECT produto_nome, quantidade, preco_unitario FROM itens_pedido WHERE pedido_id=?', (identificador,)).fetchall()
        return dict(pedido) | {'itens': [dict(i) for i in itens]}
    finally:
        con.close()


def publico(p):
    return {k: p[k] for k in ('numero', 'data', 'status', 'valor_total', 'itens')}


def criar_app(modo):
    if modo not in MODOS:
        raise ValueError(modo)
    app = FastAPI()

    def opcional(authorization: str | None = Header(None)):
        return usuario_atual(authorization) if authorization else None

    if modo == 'sem_autenticacao':
        @app.get('/pedidos/{identificador}')
        def aberto(identificador: int):
            p = buscar(identificador)
            if p is None:
                raise HTTPException(404, 'Pedido nao encontrado')
            return publico(p)
        return app

    if modo == 'token_opcional':
        @app.get('/pedidos/{identificador}')
        def parcial(identificador: int, u=Depends(opcional)):
            p = buscar(identificador)
            if p is None or (u is not None and p['usuario_id'] != u['id']):
                raise HTTPException(404, 'Pedido nao encontrado')
            return publico(p)
        return app

    @app.get('/pedidos/{identificador}')
    def pedido(identificador: int, usuario_id: int | None = None, x_user_id: int | None = Header(None), u=Depends(usuario_atual)):
        if modo == 'nega_tudo':
            raise HTTPException(404, 'Pedido nao encontrado')
        if modo == 'finge_sucesso':
            return publico(buscar(1))
        p = buscar(identificador)
        if p is None:
            raise HTTPException(404, 'Pedido nao encontrado')
        dono = u['id']
        if modo == 'dono_por_parametro' and usuario_id is not None:
            dono = usuario_id
        if modo == 'dono_por_cabecalho' and x_user_id is not None:
            dono = x_user_id
        if modo != 'sem_dono' and p['usuario_id'] != dono:
            if modo == 'responde_403':
                raise HTTPException(403, 'Acesso negado')
            raise HTTPException(404, 'Pedido de outro usuario' if modo == 'mensagem_diferente' else 'Pedido nao encontrado')
        return publico(p)

    return app


def expectativas(modo, r):
    t = {x['teste']: x['status'] for x in r['testes']}
    positivo = r['controles_positivos']
    seguranca = [x['status'] for x in r['testes'] if x['tipo'].startswith('seguranca_')]
    if modo == 'protegida':
        return positivo and all(s == 'aprovado' for s in seguranca) and t['oculta_existencia'] == 'aprovado'
    if modo in ('nega_tudo', 'finge_sucesso'):
        return not positivo and 'aprovado' not in seguranca
    if modo in ('responde_403', 'mensagem_diferente'):
        return positivo and all(s == 'aprovado' for s in seguranca) and t['oculta_existencia'] == 'reprovado'
    esperado = {
        'sem_dono': ('a_le_pedido_de_b', 'b_le_pedido_de_a'),
        'sem_autenticacao': ('a_le_pedido_de_b', 'sem_token', 'token_invalido'),
        'dono_por_parametro': ('parametro_usuario',),
        'dono_por_cabecalho': ('cabecalho_usuario',),
        'token_opcional': ('sem_token',),
    }[modo]
    return positivo and all(t[k] == 'reprovado' for k in esperado)
