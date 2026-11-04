"""T05: testa efeitos nas contas, e nao apenas respostas de sucesso."""
from contextlib import contextmanager
import hashlib
from fastapi.testclient import TestClient
from t05_infra import A,B,UNKNOWN,NEW,OTHER,criar_infra

INVALID=(400,401,403,404,410,422)


def sucesso(response):
    if response.status_code!=200:return False
    try:
        body=response.json()
        return isinstance(body,dict) and isinstance(body.get('mensagem'),str) and bool(body['mensagem'])
    except ValueError:return False


@contextmanager
def sessao(factory):
    infra=criar_infra()
    with TestClient(factory(infra),raise_server_exceptions=False,follow_redirects=False) as client:
        yield infra,client


def solicitar(infra,client,email=A):
    before=len(infra.envios)
    response=client.post('/recuperar-senha',json={'email':email})
    sent=[v for v in infra.envios[before:] if v['email']==email]
    token=sent[-1]['token'] if len(sent)==1 and isinstance(sent[-1]['token'],str) and sent[-1]['token'] else None
    return response,token


def reset(client,token,password=NEW,**extra):
    return client.post('/redefinir-senha',json={'token':token or '', 'nova_senha':password,**extra})


def rejeicao(response,infra,before,positive):
    if len(infra.alteracoes)>before:return 'reprovado'
    if not positive or response.status_code>=500:return 'inconclusivo'
    return 'aprovado' if response.status_code in INVALID else 'inconclusivo'


def avaliar(factory):
    tests=[]
    def add(name,kind,status,**evidence):tests.append(dict(teste=name,tipo=kind,status=status,evidencia=evidence))
    for email,uid in [(A,1),(B,2)]:
        with sessao(factory) as (infra,client):
            old=dict(infra.senhas);request,token=solicitar(infra,client,email)
            response=reset(client,token)
            good=sucesso(request) and token is not None and sucesso(response) and infra.senhas[uid]==NEW and all(v==infra.senhas[k] for k,v in old.items() if k!=uid)
            add('ciclo:'+email,'funcional','aprovado' if good else 'reprovado',solicitacao_http=request.status_code,redefinicao_http=response.status_code,email_capturado=token is not None,conta_alterada_corretamente=good)
    positive=all(t['status']=='aprovado' for t in tests)
    with sessao(factory) as (infra,client):
        response,token=solicitar(infra,client)
        add('sem_alteracao_na_solicitacao','seguranca', 'reprovado' if infra.alteracoes else 'aprovado' if positive and response.status_code==200 else 'inconclusivo',alteracoes=len(infra.alteracoes))
    with sessao(factory) as (infra,client):
        request,token=solicitar(infra,client);before=len(infra.alteracoes)
        response=reset(client,'T05-token-inexistente',email=A)
        add('token_inexistente','seguranca',rejeicao(response,infra,before,positive),status_http=response.status_code,alteracoes=len(infra.alteracoes)-before)
    with sessao(factory) as (infra,client):
        request,token=solicitar(infra,client);first=reset(client,token)
        valid=positive and token is not None and first.status_code==200 and infra.senhas[1]==NEW
        before=len(infra.alteracoes);response=reset(client,token,OTHER)
        add('token_reutilizado','seguranca',rejeicao(response,infra,before,valid),primeiro_http=first.status_code,segundo_http=response.status_code,alteracoes_adicionais=len(infra.alteracoes)-before)
    for elapsed in [899,900,901]:
        with sessao(factory) as (infra,client):
            request,token=solicitar(infra,client);infra.tempo+=elapsed;before=len(infra.alteracoes)
            response=reset(client,token)
            if elapsed==899:
                status='aprovado' if positive and token is not None and response.status_code==200 and infra.senhas[1]==NEW else 'reprovado'
                kind='contrato'
            else:status=rejeicao(response,infra,before,positive and token is not None);kind='seguranca'
            add('validade:'+str(elapsed),kind,status,status_http=response.status_code,segundos_decorridos=elapsed,alteracoes=len(infra.alteracoes)-before)
    # Sem exigir um valor: um token ainda aceito depois de uma semana nao expira na pratica.
    with sessao(factory) as (infra,client):
        request,token=solicitar(infra,client);infra.tempo+=604800;before=len(infra.alteracoes)
        response=reset(client,token)
        add('expira_em_uma_semana','seguranca',rejeicao(response,infra,before,positive and token is not None),status_http=response.status_code,alteracoes=len(infra.alteracoes)-before)
    with sessao(factory) as (infra,client):
        request,token=solicitar(infra,client);before=len(infra.alteracoes);old_b=infra.senhas[2]
        response=reset(client,token,email=B)
        touched_b=any(v['usuario_id']==2 for v in infra.alteracoes[before:]) or infra.senhas[2]!=old_b
        good=positive and token is not None and (response.status_code in INVALID or response.status_code==200 and infra.senhas[1]==NEW)
        add('vinculo_da_conta','seguranca','reprovado' if touched_b else 'aprovado' if good else 'inconclusivo',status_http=response.status_code,outra_conta_alterada=touched_b)
    with sessao(factory) as (infra,client):
        response,token=solicitar(infra,client)
        leaked=bool(token and (token in response.text or any(token in v for v in response.headers.values())))
        add('token_na_resposta','seguranca','reprovado' if leaked else 'aprovado' if positive and token else 'inconclusivo',token_exposto=leaked,status_http=response.status_code)
    with sessao(factory) as (infra,client):
        known,token=solicitar(infra,client);before=len(infra.envios);changes=len(infra.alteracoes)
        unknown,missing=solicitar(infra,client,UNKNOWN)
        same=known.status_code==unknown.status_code==200 and known.content==unknown.content
        extra=len(infra.envios)-before
        bad=bool(extra or len(infra.alteracoes)>changes)
        add('resposta_uniforme','seguranca','reprovado' if positive and not same or bad else 'aprovado' if positive and same else 'inconclusivo',existente_http=known.status_code,inexistente_http=unknown.status_code,corpo_identico=known.content==unknown.content,envios_para_ausente=extra)
    with sessao(factory) as (infra,client):
        tokens=[]
        for i in range(8):
            response,token=solicitar(infra,client)
            if response.status_code==200 and token:tokens.append(token)
        repeated=len(set(tokens))!=len(tokens)
        sequential=len(tokens)==8 and all(t.isdecimal() for t in tokens) and all(int(b)==int(a)+1 for a,b in zip(tokens,tokens[1:]))
        status='fraqueza_observada' if repeated or sequential else 'sem_fraqueza_observada' if len(tokens)==8 else 'inconclusivo'
        add('diagnostico_tokens','diagnostico',status,quantidade=len(tokens),repeticao=repeated,sequencia_incremental=sequential,comprimentos=[len(t) for t in tokens],sha256=[hashlib.sha256(t.encode()).hexdigest() for t in tokens],entropia_comprovada=False)
    return dict(estado='concluido',controles_positivos=positive,testes=tests,geracao_criptografica='revisao_de_codigo_pendente')
