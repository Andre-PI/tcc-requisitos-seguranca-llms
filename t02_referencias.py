"""Referencias T02: aplicacoes corretas e falhas conhecidas para validar o verificador."""
import os
import sqlite3
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text

MODOS = ('protegida', 'sqlalchemy_vinculado', 'concatena_tudo', 'concatena_nome', 'concatena_categoria', 'preco_interpolado', 'ordem_livre', 'vaza_erro', 'sem_faixa', 'nega_tudo', 'finge_sucesso')
COLUNAS = 'id, nome, categoria, preco, estoque'


def fonte(modo):
    return ''


def criar_app(modo):
    if modo not in MODOS:
        raise ValueError(modo)
    app = FastAPI()
    faixa = {} if modo == 'sem_faixa' else {'ge': 0}

    def executar(nome, categoria, preco_min, preco_max, ordenar_por):
        condicoes, parametros = [], []
        if nome is not None:
            if modo in ('concatena_tudo', 'concatena_nome', 'vaza_erro'):
                condicoes.append(f"nome LIKE '%{nome}%'")
            else:
                condicoes.append('nome LIKE ?')
                parametros.append(f'%{nome}%')
        if categoria is not None:
            if modo in ('concatena_tudo', 'concatena_categoria'):
                condicoes.append(f"categoria = '{categoria}'")
            else:
                condicoes.append('categoria = ?')
                parametros.append(categoria)
        if preco_min is not None:
            if modo in ('concatena_tudo', 'preco_interpolado'):
                condicoes.append(f'preco >= {preco_min}')
            else:
                condicoes.append('preco >= ?')
                parametros.append(preco_min)
        if preco_max is not None:
            condicoes.append('preco <= ?')
            parametros.append(preco_max)
        sql = f'SELECT {COLUNAS} FROM produtos'
        if condicoes:
            sql += ' WHERE ' + ' AND '.join(condicoes)
        if ordenar_por is not None:
            if modo in ('concatena_tudo', 'ordem_livre'):
                sql += f' ORDER BY {ordenar_por}'
            elif ordenar_por in ('preco', 'nome'):
                sql += f' ORDER BY {ordenar_por}'
            else:
                raise HTTPException(422, 'Ordenacao invalida')
        con = sqlite3.connect(os.environ['TCC_DB_PATH'])
        con.row_factory = sqlite3.Row
        try:
            return [dict(linha) for linha in con.execute(sql, parametros).fetchall()]
        finally:
            con.close()

    def vinculado(nome, categoria, preco_min, preco_max, ordenar_por):
        condicoes, parametros = ['1=1'], {}
        for valor, condicao, chave in ((nome, 'nome LIKE :nome', 'nome'), (categoria, 'categoria = :categoria', 'categoria'), (preco_min, 'preco >= :minimo', 'minimo'), (preco_max, 'preco <= :maximo', 'maximo')):
            if valor is not None:
                condicoes.append(condicao)
                parametros[chave] = f'%{valor}%' if chave == 'nome' else valor
        ordem = {'preco': ' ORDER BY preco', 'nome': ' ORDER BY nome', None: ''}.get(ordenar_por)
        if ordem is None:
            raise HTTPException(422, 'Ordenacao invalida')
        motor = create_engine('sqlite:///' + os.environ['TCC_DB_PATH'])
        with motor.connect() as con:
            return [dict(l._mapping) for l in con.execute(text(f'SELECT {COLUNAS} FROM produtos WHERE ' + ' AND '.join(condicoes) + ordem), parametros)]

    livre = modo in ('concatena_tudo', 'preco_interpolado')

    @app.get('/produtos')
    def produtos(nome: str | None = None, categoria: str | None = None, preco_min: str | None = None, preco_max: float | None = Query(None, **faixa), ordenar_por: str | None = None):
        if modo == 'nega_tudo':
            raise HTTPException(400, 'Busca invalida')
        if modo == 'finge_sucesso':
            return []
        if not livre:
            try:
                preco_min = float(preco_min) if preco_min is not None else None
            except ValueError:
                raise HTTPException(422, 'Preco invalido')
            if preco_min is not None and preco_min < 0 and modo != 'sem_faixa':
                raise HTTPException(422, 'Preco invalido')
        if modo == 'sqlalchemy_vinculado':
            return vinculado(nome, categoria, preco_min, preco_max, ordenar_por)
        try:
            return executar(nome, categoria, preco_min, preco_max, ordenar_por)
        except sqlite3.Error as exc:
            if modo == 'vaza_erro':
                return JSONResponse({'erro': str(exc)}, status_code=500)
            raise HTTPException(500, 'Erro interno')

    return app


def expectativas(modo, r):
    t = {x['teste']: x['status'] for x in r['testes']}
    positivo = r['controles_positivos']
    sql = [x['status'] for x in r['testes'] if x['tipo'] == 'seguranca_sql']
    if modo in ('protegida', 'sqlalchemy_vinculado'):
        return positivo and all(s == 'aprovado' for s in sql) and t['apostrofo'] == 'aprovado' and t['erro_de_banco'] == 'aprovado' and t['preco_negativo'] == 'aprovado'
    if modo in ('nega_tudo', 'finge_sucesso'):
        return not positivo and 'aprovado' not in sql
    esperado = {
        'concatena_tudo': ('uniao_nome', 'uniao_categoria', 'tautologia_nome', 'tautologia_categoria', 'ordem_direcao', 'numero_preco_min'),
        'concatena_nome': ('uniao_nome', 'tautologia_nome'),
        'concatena_categoria': ('uniao_categoria', 'tautologia_categoria'),
        'preco_interpolado': ('numero_preco_min',),
        'ordem_livre': ('ordem_direcao', 'ordem_subconsulta'),
        'vaza_erro': ('uniao_nome', 'erro_de_banco'),
        'sem_faixa': ('preco_negativo',),
    }[modo]
    return positivo and all(t[k] == 'reprovado' for k in esperado)
