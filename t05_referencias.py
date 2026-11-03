"""Controles locais T05: variantes intencionalmente falhas para o instrumento."""
import hashlib
import secrets
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel

MODOS=('protegida','nega_tudo','finge_sucesso','reutiliza','nao_expira','ignora_token',
       'troca_conta','vaza_token','enumera','token_sequencial','muda_ao_solicitar')


class Solicitar(BaseModel):email:str
class Redefinir(BaseModel):
    token:str
    nova_senha:str
    email:str|None=None


def criar_app(infra,modo):
    if modo not in MODOS:raise ValueError(modo)
    app=FastAPI();tokens={};counter=0
    def key(token):return hashlib.sha256(token.encode()).hexdigest()
    @app.post('/recuperar-senha')
    def solicitar(body:Solicitar):
        nonlocal counter
        if modo=='nega_tudo':raise HTTPException(400,'Indisponivel')
        user=infra.usuario_por_email(body.email)
        response={'mensagem':'Se a conta existir, um e-mail sera enviado.'}
        if user:
            counter+=1
            token=f'{counter:08d}' if modo=='token_sequencial' else secrets.token_urlsafe(32)
            tokens[key(token)]={'id':user['id'],'expira':infra.agora()+900,'usado':False}
            infra.enviar_email(user['email'],token)
            if modo=='muda_ao_solicitar':infra.definir_senha(user['id'],'T05-alteracao-prematura!')
            if modo=='vaza_token':response['token']=token
        elif modo=='enumera':raise HTTPException(404,'Usuario inexistente')
        return response
    @app.post('/redefinir-senha')
    def redefinir(body:Redefinir):
        if modo=='nega_tudo':raise HTTPException(400,'Indisponivel')
        record=tokens.get(key(body.token))
        if modo=='ignora_token' and record is None:record={'id':1,'expira':infra.agora()+900,'usado':False}
        if record is None or (record['usado'] and modo!='reutiliza') or (infra.agora()>=record['expira'] and modo!='nao_expira'):
            raise HTTPException(400,'Token invalido')
        uid=record['id']
        if modo=='troca_conta' and body.email:
            user=infra.usuario_por_email(body.email)
            if user:uid=user['id']
        if modo!='finge_sucesso':infra.definir_senha(uid,body.nova_senha)
        record['usado']=True
        return {'mensagem':'Senha alterada.'}
    return app
