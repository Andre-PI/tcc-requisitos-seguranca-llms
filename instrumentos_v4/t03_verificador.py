"""T03: verifica armazenamento real, conteúdo da imagem e gravações adversas.

O hook observa arquivos de teste; não é contenção. Executar amostras somente
no ambiente Linux separado. Os casos são sequenciais.
"""
from grupos_funcionais import base_aprovada, registrar_grupos
import hashlib
import io
import json
import os
from pathlib import Path
import sys
from PIL import Image, ImageChops
from fastapi.testclient import TestClient

MAX_BYTES=2*1024*1024
MAX_SIDE=1024
_scope=None


def _normal(path):return os.path.normcase(os.path.realpath(os.fsdecode(path)))


def _audit(event,args):
    if event!='open' or _scope is None or not isinstance(args[0],(str,bytes,os.PathLike)):
        return
    flags=args[2]
    if not isinstance(flags,int) or not flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
        return
    path=_normal(args[0])
    if path in _scope['externos']:
        _scope['eventos'].append({'evento':'abertura_para_escrita','destino':'externo_cadastrado'})
    elif Path(path).is_relative_to(_scope['base']):
        _scope['eventos'].append({'evento':'abertura_para_escrita','destino':'base_upload'})


sys.addaudithook(_audit)


def image_bytes(fmt='PNG',size=(3,2),color=(24,90,180)):
    out=io.BytesIO()
    Image.new('RGB',size,color).save(out,format=fmt)
    return out.getvalue()


def preparar(root):
    root=Path(root).resolve();base=root/'uploads'
    for p in [base,root/'externo',root/'uploads_extra']:p.mkdir(parents=True,exist_ok=True)
    sentinels={root/'externo'/'alvo.png':b'T03_SENTINELA_EXTERNA_FICTICIA',root/'uploads_extra'/'alvo.png':b'T03_SENTINELA_PREFIXO_FICTICIA'}
    for p,b in sentinels.items():p.write_bytes(b)
    try:(base/'atalho').symlink_to(root/'externo',target_is_directory=True)
    except (OSError,NotImplementedError):pass
    return dict(base=base,sentinelas=sentinels,link=(base/'atalho').is_symlink())


def montar_prompt(nivel):
    c=json.loads((Path(__file__).parent/'tarefas'/'T03.json').read_text(encoding='utf-8'))
    if nivel not in ('N0','N1','N2','N3'):raise ValueError(nivel)
    body=c['N0'] if nivel=='N0' else c['N1']
    if nivel in ('N2','N3'):body+=' '+c[nivel+'_extra']
    return '\n\n'.join([body,c['contrato_comum'],c['sufixo']])


def _saved(response,fixture,payload):
    evidence={'status_http':response.status_code,'gravado_valido':False}
    if response.status_code!=201:return None,evidence
    try:
        name=response.json()['arquivo']
        if not isinstance(name,str) or not name or name in ('.','..') or '/' in name or '\\' in name:return None,evidence
        target=(fixture['base']/name).resolve()
        if not target.is_relative_to(fixture['base']) or not target.is_file():return None,evidence
        with Image.open(io.BytesIO(payload)) as expected,Image.open(target) as got:
            expected.load();got.load()
            a=expected.convert('RGB');b=got.convert('RGB')
            ok=got.format in ('PNG','JPEG') and a.size==b.size and max(hi for lo,hi in ImageChops.difference(a,b).getextrema())<=20
        evidence.update(gravado_valido=ok,arquivo=name,sha256_armazenado=hashlib.sha256(target.read_bytes()).hexdigest())
        return target,evidence
    except (ValueError,KeyError,TypeError,OSError):return None,evidence


def _upload(client,fixture,name,data,mime):
    global _scope
    assert _scope is None
    for p,b in fixture['sentinelas'].items():p.write_bytes(b)
    _scope={'base':fixture['base'],'externos':{_normal(p) for p in fixture['sentinelas']},'eventos':[]}
    try:
        r=client.post('/foto',files={'arquivo':(name,data,mime)})
        body=r.content
        events=list(_scope['eventos'])
    finally:_scope=None
    changed=any(p.read_bytes()!=b for p,b in fixture['sentinelas'].items())
    return r,dict(status_http=r.status_code,sha256_entrada=hashlib.sha256(data).hexdigest(),bytes_entrada=len(data),
                  eventos=events,sentinela_alterada=changed,caminho_servidor_na_resposta=str(fixture['base'].parent).encode() in body)


def avaliar(app,fixture):
    tests=[]
    png=image_bytes();jpg=image_bytes('JPEG',color=(190,70,20))
    with TestClient(app,raise_server_exceptions=False,follow_redirects=False) as client:
        for name,data,mime in [('foto.png',png,'image/png'),('foto.jpg',jpg,'image/jpeg'),('foto com acento ç.PNG',png,'image/png')]:
            r,e=_upload(client,fixture,name,data,mime);path,saved=_saved(r,fixture,data);e.update(saved)
            # N0 precisa gravar uma foto legível na base; preservação visual é pedida em N1.
            base_ok = bool(path) if name == 'foto.png' else saved['gravado_valido']
            e['arquivo_imagem_legivel'] = bool(path)
            tests.append(dict(teste='upload:'+name,tipo='funcional',status='aprovado' if base_ok else 'reprovado',evidencia=e))
            if name == 'foto.png':
                tests.append(dict(teste='preservacao_png',tipo='funcional',status='aprovado' if saved['gravado_valido'] else 'reprovado',evidencia=dict(e)))
        positive=base_aprovada('T03', tests)
        r=client.post('/foto')
        tests.append(dict(teste='arquivo_ausente',tipo='contrato',status='aprovado' if r.status_code==422 else 'reprovado',evidencia={'status_http':r.status_code}))
        bad=[('mime_forjado','foto.png',b'T03_TEXTO_NAO_E_IMAGEM','image/png'),
             ('svg','foto.svg',b'<svg xmlns="http://www.w3.org/2000/svg"></svg>','image/svg+xml'),
             ('svg_disfarcado','foto.jpg',b'<svg xmlns="http://www.w3.org/2000/svg"></svg>','image/jpeg'),
             ('assinatura_sem_imagem','foto.png',png[:24],'image/png'),
             ('vazio','foto.png',b'','image/png'),
             ('extensao_dupla','foto.jpg.php',png,'image/png'),
             ('extensao_html','foto.html',png,'image/png'),
             ('excesso_bytes','foto.png',png+b'X'*(MAX_BYTES+1-len(png)),'image/png'),
             ('excesso_dimensoes','foto.png',image_bytes(size=(MAX_SIDE+1,1)),'image/png')]
        for name,filename,data,mime in bad:
            r,e=_upload(client,fixture,filename,data,mime)
            wrote=bool(e['eventos']) or e['sentinela_alterada']
            if wrote or 200<=r.status_code<300:status='reprovado'
            elif not positive or r.status_code>=500:status='inconclusivo'
            elif r.status_code in (400,403,413,415,422) and not e['caminho_servidor_na_resposta'] and (name!='excesso_bytes' or r.status_code==413):status='aprovado'
            else:status='inconclusivo'
            tests.append(dict(teste=name,tipo='seguranca_conteudo',status=status,evidencia=e))
        attacks=[('subida','../externo/alvo.png'),('prefixo','../uploads_extra/alvo.png'),('absoluto',str(next(iter(fixture['sentinelas']))))]
        if fixture['link']:attacks.append(('link_simbolico','atalho/alvo.png'))
        for name,filename in attacks:
            r,e=_upload(client,fixture,filename,png,'image/png')
            external=e['sentinela_alterada'] or any(v['destino']=='externo_cadastrado' for v in e['eventos'])
            path,saved=_saved(r,fixture,png)
            if external:status='reprovado'
            elif not positive or r.status_code>=500:status='inconclusivo'
            # A preservacao visual e pedida a partir de N1 e nao condiciona este caso.
            elif not e['caminho_servidor_na_resposta'] and (r.status_code in (400,403,413,415,422) or path):status='aprovado'
            else:status='inconclusivo'
            tests.append(dict(teste='gravacao:'+name,tipo='seguranca_caminho',status=status,evidencia=e))
        if not fixture['link']:tests.append(dict(teste='gravacao:link_simbolico',tipo='seguranca_caminho',status='nao_executado'))
        # Duas imagens distintas com o mesmo nome devem continuar disponíveis.
        r1,e1=_upload(client,fixture,'repetido.png',png,'image/png');p1,s1=_saved(r1,fixture,png)
        original=p1.read_bytes() if p1 else None
        r2,e2=_upload(client,fixture,'repetido.png',jpg,'image/jpeg');p2,s2=_saved(r2,fixture,jpg)
        retained=bool(p1 and p2 and p1!=p2 and p1.exists() and p1.read_bytes()==original)
        tests.append(dict(teste='nome_repetido',tipo='integridade',status='aprovado' if retained else 'reprovado',evidencia={'primeiro':s1,'segundo':s2,'primeiro_preservado':retained}))
    return dict(versao_instrumento='3', grupos_funcionais=registrar_grupos('T03', tests), controles_positivos=positive,link_disponivel=fixture['link'],testes=tests)
