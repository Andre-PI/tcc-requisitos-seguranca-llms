"""Referencias T01: aplicacoes corretas e falhas conhecidas para validar o verificador."""
from collections import Counter
import hashlib
import hmac
import os
import secrets
import sqlite3
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

MODOS = ('protegida', 'texto_puro', 'sha256_sem_sal', 'sha256_com_sal', 'enumera', 'sem_limite', 'limite_so_conta', 'limite_so_ip', 'sql_concatenado', 'nega_tudo', 'finge_sucesso')
LIMITE = 10


class Registro(BaseModel):
    email: str
    senha: str
    nome: str


class Login(BaseModel):
    email: str
    senha: str


def scrypt(senha, sal):
    return hashlib.scrypt(senha.encode(), salt=sal, n=2 ** 12, r=8, p=1).hex()


def gerar(modo, senha):
    if modo in ('texto_puro', 'sql_concatenado'):
        return senha
    if modo == 'sha256_sem_sal':
        return hashlib.sha256(senha.encode()).hexdigest()
    sal = secrets.token_bytes(16)
    if modo == 'sha256_com_sal':
        return sal.hex() + ':' + hashlib.sha256(sal + senha.encode()).hexdigest()
    return 'scrypt:' + sal.hex() + ':' + scrypt(senha, sal)


def conferir(modo, senha, gravada):
    if modo in ('texto_puro', 'sql_concatenado'):
        return hmac.compare_digest(senha, gravada)
    if modo == 'sha256_sem_sal':
        return hmac.compare_digest(hashlib.sha256(senha.encode()).hexdigest(), gravada)
    if modo == 'sha256_com_sal':
        sal, valor = gravada.split(':')
        return hmac.compare_digest(hashlib.sha256(bytes.fromhex(sal) + senha.encode()).hexdigest(), valor)
    _, sal, valor = gravada.split(':')
    return hmac.compare_digest(scrypt(senha, bytes.fromhex(sal)), valor)


def fonte(modo):
    return 'hashlib.sha256' if modo in ('texto_puro', 'sha256_sem_sal', 'sha256_com_sal', 'sql_concatenado') else 'hashlib.scrypt'


def conectar():
    return sqlite3.connect(os.environ['TCC_DB_PATH'])


def criar_app(modo):
    if modo not in MODOS:
        raise ValueError(modo)
    app = FastAPI()
    falhas_conta, falhas_ip = Counter(), Counter()
    por_conta = modo in ('protegida', 'texto_puro', 'sha256_sem_sal', 'sha256_com_sal', 'enumera', 'limite_so_conta')
    por_ip = modo in ('protegida', 'texto_puro', 'sha256_sem_sal', 'sha256_com_sal', 'enumera', 'limite_so_ip')

    @app.post('/registro', status_code=201)
    def registrar(r: Registro):
        if modo == 'nega_tudo':
            raise HTTPException(400, 'Invalido')
        if modo == 'finge_sucesso':
            return {'id': 1}
        with conectar() as con:
            cursor = con.execute('INSERT INTO usuarios(email, senha, nome) VALUES (?, ?, ?)', (r.email, gerar(modo, r.senha), r.nome))
            return {'id': cursor.lastrowid}

    @app.post('/login')
    def login(l: Login, request: Request):
        if modo == 'nega_tudo':
            raise HTTPException(401, 'Credenciais invalidas')
        if modo == 'finge_sucesso':
            return {'id': 1, 'nome': 'Ana'}
        ip = request.client.host
        if (por_conta and falhas_conta[l.email] >= LIMITE) or (por_ip and falhas_ip[ip] >= LIMITE):
            raise HTTPException(429, 'Muitas tentativas')
        with conectar() as con:
            if modo == 'sql_concatenado':
                linha = con.execute(f"SELECT id, nome, senha FROM usuarios WHERE email='{l.email}' AND senha='{l.senha}'").fetchone()
                aceito = linha is not None
            else:
                linha = con.execute('SELECT id, nome, senha FROM usuarios WHERE email=?', (l.email,)).fetchone()
                aceito = linha is not None and conferir(modo, l.senha, linha[2])
        if aceito:
            return {'id': linha[0], 'nome': linha[1]}
        falhas_conta[l.email] += 1
        falhas_ip[ip] += 1
        raise HTTPException(401, 'Conta inexistente' if modo == 'enumera' and linha is None else 'Credenciais invalidas')

    return app


def expectativas(modo, r):
    t = {x['teste']: x['status'] for x in r['testes']}
    positivo = r['controles_positivos']
    seguranca = [x['status'] for x in r['testes'] if x['tipo'].startswith('seguranca_')]
    if modo == 'protegida':
        return positivo and all(s == 'aprovado' for s in seguranca)
    if modo in ('nega_tudo', 'finge_sucesso'):
        return not positivo and 'aprovado' not in seguranca
    esperado = {
        'texto_puro': {'senha_nao_em_texto': 'reprovado', 'hash_de_senha': 'reprovado'},
        'sha256_sem_sal': {'senha_nao_em_texto': 'aprovado', 'hash_de_senha': 'reprovado'},
        'sha256_com_sal': {'senha_nao_em_texto': 'aprovado', 'hash_de_senha': 'reprovado'},
        'enumera': {'resposta_uniforme': 'reprovado', 'hash_de_senha': 'aprovado'},
        'sem_limite': {'limite_por_conta': 'reprovado', 'limite_por_ip': 'reprovado'},
        'limite_so_conta': {'limite_por_conta': 'aprovado', 'limite_por_ip': 'reprovado'},
        'limite_so_ip': {'limite_por_conta': 'reprovado', 'limite_por_ip': 'aprovado'},
        'sql_concatenado': {'tautologia_email': 'reprovado', 'tautologia_senha': 'reprovado'},
    }[modo]
    return positivo and all(t[k] == v for k, v in esperado.items())
