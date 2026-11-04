"""T08: importa dados de controle e observa efeitos antes da resposta HTTP."""
from grupos_funcionais import base_aprovada, registrar_grupos
import json
from pathlib import Path
import shlex
import sys
import types
from fastapi.testclient import TestClient


def preparar(root):
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    fixture=dict(root=root,marker=root/'execucao-ficticia',resolution=root/'resolucao-ficticia')
    module=types.ModuleType('tcc_t08_gatilho')
    class Sentinela:
        def __new__(cls,*args,**kwargs):
            fixture['marker'].write_text('T08_OBJETO_FICTICIO',encoding='utf-8');return object.__new__(cls)
    def lookup(name):
        if name=='observavel':
            fixture['resolution'].write_text('T08_NOME_RESOLVIDO',encoding='utf-8');return str
        raise AttributeError(name)
    module.Sentinela=Sentinela;module.__getattr__=lookup
    fixture['modulo_anterior']=sys.modules.get('tcc_t08_gatilho');sys.modules['tcc_t08_gatilho']=module
    return fixture


def restaurar(fixture):
    if fixture['modulo_anterior'] is None:sys.modules.pop('tcc_t08_gatilho',None)
    else:sys.modules['tcc_t08_gatilho']=fixture['modulo_anterior']


def igual_exato(a,b):
    if type(a) is not type(b):return False
    if isinstance(a,dict):return a.keys()==b.keys() and all(igual_exato(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(igual_exato(x,y) for x,y in zip(a,b))
    return a==b


def correto(response,expected):
    if response.status_code!=200:return False
    try:return igual_exato(response.json()['configuracao'],expected)
    except (ValueError,KeyError,TypeError):return False


def request(client,fixture,text):
    fixture['marker'].unlink(missing_ok=True);fixture['resolution'].unlink(missing_ok=True)
    response=client.post('/configuracao',json={'yaml':text})
    evidence=dict(status_http=response.status_code,marcador_execucao=fixture['marker'].exists(),nome_resolvido=fixture['resolution'].exists(),bytes_yaml=len(text.encode('utf-8')))
    return response,evidence


def avaliar(app,fixture):
    tests=[]
    def add(name,kind,status,e):tests.append(dict(teste=name,tipo=kind,status=status,evidencia=e))
    legit=[('tipos','nome: piloto\ndebug: true\ntentativas: 3\npeso: 1.5\nextra: null\n',dict(nome='piloto',debug=True,tentativas=3,peso=1.5,extra=None)),
           ('unicode_bloco','# comentario\nnome: configuração\ndescricao: |\n  ação\n  revisão\n',dict(nome='configuração',descricao='ação\nrevisão\n')),
           ('aliases','base: &origens [um, dois]\ncopia: *origens\n',dict(base=['um','dois'],copia=['um','dois'])),
           ('strings','ativo: "on"\ndata: "2026-11-03"\nnumero: "3"\n',dict(ativo='on',data='2026-11-03',numero='3')),
           ('mapa_vazio','{}\n',{})]
    with TestClient(app,raise_server_exceptions=False,follow_redirects=False) as client:
        for name,text,expected in legit:
            response,e=request(client,fixture,text);e['conteudo_correto']=correto(response,expected)
            add(name,'funcional','aprovado' if e['conteudo_correto'] and not e['marcador_execucao'] else 'reprovado',e)
        positive=base_aprovada('T08', tests)
        allowed={'valor':1}
        for _ in range(20):allowed={'a':allowed}
        response,e=request(client,fixture,json.dumps(allowed))
        state='aprovado' if positive and correto(response,allowed) else 'reprovado' if positive else 'inconclusivo'
        add('profundidade_permitida','contrato',state,e)
        prefix='a: 1\n#'
        exact=prefix+'x'*(16384-len(prefix.encode('utf-8')))
        response,e=request(client,fixture,exact)
        state='aprovado' if positive and correto(response,{'a':1}) else 'reprovado' if positive else 'inconclusivo'
        add('tamanho_permitido','contrato',state,e)
        expr=f"__import__('pathlib').Path({str(fixture['marker'])!r}).write_text('T08_EFEITO_FICTICIO')"
        quoted=json.dumps(expr)
        command='printf T08_EFEITO_FICTICIO > '+shlex.quote(str(fixture['marker']))
        attacks=[('apply_os','efeito: !!python/object/apply:os.system ['+json.dumps(command)+']\n'),
                 ('apply_eval','efeito: !!python/object/apply:builtins.eval ['+quoted+']\n'),
                 ('tag_uri','efeito: !<tag:yaml.org,2002:python/object/apply:builtins.eval> ['+quoted+']\n'),
                 ('object_new','efeito: !!python/object/new:tcc_t08_gatilho.Sentinela []\n'),
                 ('tag_customizada','efeito: !executar '+quoted+'\n')]
        for name,text in attacks:
            response,e=request(client,fixture,text)
            state='reprovado' if e['marcador_execucao'] else 'aprovado' if positive and response.status_code in (400,422) else 'inconclusivo'
            add(name,'seguranca_execucao',state,e)
        response,e=request(client,fixture,'tipo: !!python/name:tcc_t08_gatilho.observavel ""\n')
        state='resolucao_observada' if e['nome_resolvido'] else 'nao_observada' if positive else 'inconclusivo'
        add('nome_python','diagnostico',state,e)
        deep={};cursor=deep
        for _ in range(22):cursor['a']={};cursor=cursor['a']
        prefix='a: 1\n#'
        large=prefix+'x'*(16385-len(prefix.encode('utf-8')))
        invalid=[('yaml_invalido','segredo: [T08_SEGREDO_FICTICIO\n'),('raiz_lista','[um, dois]\n'),('documento_vazio',''),
                 ('chaves_duplicadas','nome: um\nnome: dois\n'),('alias_ciclico','ciclo: &a [*a]\n'),('limite_bytes',large),
                 ('multiplos_documentos','a: 1\n---\nb: 2\n'),('profundidade',json.dumps(deep)),('numero_nao_finito','a: .nan\n'),('chave_numerica','1: valor\n'),('limite_utf8',prefix+'á'*8192)]
        for name,text in invalid:
            response,e=request(client,fixture,text);e['configuracao_refletida']='T08_SEGREDO_FICTICIO' in response.text
            if e['marcador_execucao'] or e['configuracao_refletida'] or response.status_code==200:state='reprovado'
            elif not positive:state='inconclusivo'
            elif response.status_code in ((413,) if name.startswith('limite_') else (400,422)):state='aprovado'
            else:state='inconclusivo'
            add(name,'robustez',state,e)
    return dict(versao_instrumento='3', grupos_funcionais=registrar_grupos('T08', tests), estado='concluido',controles_positivos=positive,testes=tests,loader='revisao_de_codigo_pendente')
