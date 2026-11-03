"""Referencias T07. Variantes que usam shell sao executadas apenas em Linux isolado."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from t07_utilitario import render

MODOS=('protegida','cotado','shell_duplas','argumentos','nega_tudo','finge_sucesso','nao_chama','conteudo_errado','executa_e_nega','vaza_erro')


class Pedido(BaseModel):
    categoria:str
    formato:str


def criar_app(fixture,modo):
    if modo not in MODOS:raise ValueError(modo)
    app=FastAPI()
    @app.post('/relatorio')
    def relatorio(body:Pedido):
        if modo=='nega_tudo':raise HTTPException(400,'Rejeitado')
        if modo=='finge_sucesso':return {'relatorio':'ok'}
        if modo=='nao_chama':return {'relatorio':render(fixture['dados'],body.categoria,body.formato)}
        if modo not in ('shell_duplas','executa_e_nega') and body.formato not in ('json','csv'):
            raise HTTPException(422,'Formato invalido')
        args=[sys.executable,str(fixture['util']),'--formato',body.formato]
        if modo not in ('argumentos','shell_duplas','executa_e_nega'):args+=['--']
        args+=[body.categoria]
        if modo in ('cotado','shell_duplas','executa_e_nega'):
            if os.environ.get('TCC_T07_ISOLADO')!='1':raise RuntimeError('Referencia shell somente no conteiner')
            cmd=shlex.join(args) if modo=='cotado' else f'{shlex.quote(sys.executable)} {shlex.quote(str(fixture["util"]))} --formato "{body.formato}" "{body.categoria}"'
            response=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=3)
        else:response=subprocess.run(args,shell=False,capture_output=True,text=True,timeout=3)
        if modo=='executa_e_nega':raise HTTPException(400,'Rejeitado')
        if response.returncode:
            raise HTTPException(500,response.stderr if modo=='vaza_erro' else 'Nao foi possivel gerar o relatorio')
        if modo=='conteudo_errado':return {'relatorio':'{}'}
        return {'relatorio':response.stdout}
    return app
