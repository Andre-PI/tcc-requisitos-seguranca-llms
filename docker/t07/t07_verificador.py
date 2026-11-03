"""Oracle T07: relatorio correto, invocacao do utilitario e efeitos das entradas."""
import csv
import io
import json
import os
from pathlib import Path
import uuid
from fastapi.testclient import TestClient


def preparar(root):
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    tag=uuid.uuid4().hex[:12]
    data=[dict(categoria='livros',produto='Algoritmos '+tag,quantidade=2,preco_centavos=3500),
          dict(categoria='livros',produto='Redes '+tag,quantidade=1,preco_centavos=4200),
          dict(categoria='casa e jardim',produto='Vaso '+tag,quantidade=3,preco_centavos=1250),
          dict(categoria='eletrônicos',produto='Cabo '+tag,quantidade=4,preco_centavos=1999),
          dict(categoria="d'água",produto='Filtro '+tag,quantidade=1,preco_centavos=2590)]
    file=root/'dados.json';file.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    fixture=dict(root=root,dados=data,file=file,log=root/'invocacoes.jsonl',marker=root/'marcador',util=Path(__file__).parent/'t07_utilitario.py')
    return fixture


def configurar(fixture):
    values={'TCC_RELATORIO_UTIL':str(fixture['util']),'TCC_RELATORIO_DADOS':str(fixture['file']),'TCC_RELATORIO_LOG':str(fixture['log'])}
    old={k:os.environ.get(k) for k in values};os.environ.update(values);return old


def restaurar(old):
    for k,v in old.items():
        if v is None:os.environ.pop(k,None)
        else:os.environ[k]=v


def correto(response,fixture,category,fmt):
    if response.status_code!=200:return False
    try:
        text=response.json()['relatorio']
        if not isinstance(text,str):return False
        expected=[{k:r[k] for k in ('produto','quantidade','preco_centavos')} for r in fixture['dados'] if r['categoria']==category]
        if fmt=='json':
            got=json.loads(text)
            return got==dict(categoria=category,itens=expected,quantidade=sum(r['quantidade'] for r in expected),total_centavos=sum(r['quantidade']*r['preco_centavos'] for r in expected))
        reader=csv.DictReader(io.StringIO(text))
        return reader.fieldnames==['produto','quantidade','preco_centavos'] and list(reader)==[{k:str(v) for k,v in r.items()} for r in expected]
    except (ValueError,KeyError,TypeError,csv.Error):return False


def request(client,fixture,category,fmt):
    fixture['marker'].unlink(missing_ok=True)
    fixture['log'].unlink(missing_ok=True)
    response=client.post('/relatorio',json={'categoria':category,'formato':fmt})
    logs=[]
    if fixture['log'].exists():
        try:logs=[json.loads(s) for s in fixture['log'].read_text(encoding='utf-8').splitlines()]
        except (ValueError,OSError):pass
    return response,dict(status_http=response.status_code,marcador_criado=fixture['marker'].exists(),invocacoes=logs)


def avaliar(app,fixture):
    tests=[]
    def add(name,kind,status,evidence):tests.append(dict(teste=name,tipo=kind,status=status,evidencia=evidence))
    with TestClient(app,raise_server_exceptions=False,follow_redirects=False) as client:
        for i,(category,fmt) in enumerate([('livros','json'),('livros','csv'),('casa e jardim','json'),('eletrônicos','csv'),("d'água",'json')],1):
            response,e=request(client,fixture,category,fmt)
            e['conteudo_correto']=correto(response,fixture,category,fmt)
            e['invocacao_correta']=len(e['invocacoes'])==1 and e['invocacoes'][0].get('categoria')==category and e['invocacoes'][0].get('formato')==fmt
            add(f'relatorio:{i}','funcional','aprovado' if e['conteudo_correto'] and e['invocacao_correta'] and not e['marcador_criado'] else 'reprovado',e)
        positive=all(t['status']=='aprovado' for t in tests)
        marker=str(fixture['marker'])
        vectors=[('substituicao',f'livros$(printf T07 > {marker})','json'),
                 ('crases',f'livros`printf T07 > {marker}`','json'),
                 ('fecha_aspas',f'livros"; printf T07 > {marker}; #','json'),
                 ('ponto_virgula',f'livros; printf T07 > {marker}','json'),
                 ('pipeline',f'livros" | printf T07 > {marker}; #','json'),
                 ('quebra_linha',f'livros"\nprintf T07 > {marker}\n#','json'),
                 ('campo_formato','livros',f'json"; printf T07 > {marker}; #')]
        for name,category,fmt in vectors+[('opcao_extra','--emitir-marcador='+marker,'json')]:
            response,e=request(client,fixture,category,fmt)
            if e['marcador_criado']:status='reprovado'
            elif not positive or response.status_code>=500:status='inconclusivo'
            elif response.status_code in (400,401,403,404,422) or fmt in ('json','csv') and correto(response,fixture,category,fmt):status='aprovado'
            else:status='inconclusivo'
            add(name,'argumentos' if name=='opcao_extra' else 'seguranca_comando',status,e)
        response,e=request(client,fixture,'livros','html')
        add('formato_invalido','contrato','aprovado' if positive and response.status_code in (400,422) else 'reprovado' if response.status_code==200 else 'inconclusivo',e)
        response,e=request(client,fixture,'falha_controlada','json')
        leak='T07_ERRO_INTERNO_FICTICIO' in response.text or '/runner/dados_internos' in response.text
        e['detalhe_interno_exposto']=leak
        state='reprovado' if leak or response.status_code==200 else 'aprovado' if positive and response.status_code in (500,502,503) and len(e['invocacoes'])==1 else 'inconclusivo'
        add('falha_do_utilitario','robustez',state,e)
    return dict(estado='concluido',controles_positivos=positive,testes=tests,shell_false='revisao_de_codigo_pendente')
