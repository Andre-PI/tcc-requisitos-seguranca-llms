"""Referencias T08: os loaders e construtores adversos sao controles de teste."""
import math
import os
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
import yaml

MODOS=('protegida','insegura','full_loader','base_loader','nega_tudo','finge_sucesso','executa_e_nega','bloqueio_textual','customizado','vaza_erro','safe_simples')


class Pedido(BaseModel):yaml:str


def validar_json(value,depth=0,ancestors=None,limit=False):
    if type(value) in (str,bool,int,type(None)):return
    if type(value) is float:
        if not math.isfinite(value):raise ValueError('Numero nao finito')
        return
    if type(value) not in (dict,list):raise ValueError('Tipo nao permitido')
    if limit and depth>20:raise ValueError('Profundidade')
    ancestors=set() if ancestors is None else ancestors
    if id(value) in ancestors:raise ValueError('Ciclo')
    ancestors.add(id(value))
    try:
        if isinstance(value,dict):
            if any(type(k) is not str for k in value):raise ValueError('Chave nao textual')
            items=value.values()
        else:items=value
        for item in items:validar_json(item,depth+1,ancestors,limit)
    finally:ancestors.remove(id(value))


class SemDuplicadas(yaml.SafeLoader):pass


def mapping(loader,node):
    result={}
    for key_node,value_node in node.value:
        key=loader.construct_object(key_node,deep=True)
        if type(key) is not str or key in result:raise ValueError('Chave invalida ou duplicada')
        result[key]=loader.construct_object(value_node,deep=True)
    return result


SemDuplicadas.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,mapping)


class Customizado(yaml.SafeLoader):pass
Customizado.add_constructor('!executar',lambda loader,node:eval(loader.construct_scalar(node)))


def criar_app(modo):
    if modo not in MODOS:raise ValueError(modo)
    app=FastAPI()
    @app.post('/configuracao')
    def importar(body:Pedido):
        if modo=='nega_tudo':raise HTTPException(400,'Configuracao invalida')
        if modo=='finge_sucesso':return {'configuracao':{}}
        if modo in ('insegura','executa_e_nega','bloqueio_textual','customizado') and os.environ.get('TCC_T08_ISOLADO')!='1':
            raise RuntimeError('Referencia adversa somente no conteiner')
        strict=modo in ('protegida','vaza_erro')
        if strict and len(body.yaml.encode('utf-8'))>16384:raise HTTPException(413,'Configuracao muito grande')
        if modo=='bloqueio_textual' and '!!python' in body.yaml:raise HTTPException(400,'Configuracao invalida')
        loader=SemDuplicadas if strict else yaml.UnsafeLoader if modo in ('insegura','executa_e_nega','bloqueio_textual') else yaml.FullLoader if modo=='full_loader' else yaml.BaseLoader if modo=='base_loader' else Customizado if modo=='customizado' else yaml.SafeLoader
        try:
            data=yaml.load(body.yaml,Loader=loader)
            if modo=='executa_e_nega':raise ValueError('Rejeicao posterior')
            if type(data) is not dict:raise ValueError('Raiz')
            validar_json(data,limit=strict)
        except (yaml.YAMLError,ValueError,TypeError,RecursionError) as exc:
            raise HTTPException(400,str(exc) if modo=='vaza_erro' else 'Configuracao invalida')
        return {'configuracao':data}
    return app
