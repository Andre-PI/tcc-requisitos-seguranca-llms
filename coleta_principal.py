"""Coleta principal: 800 geracoes, avaliacao no Docker e analise estatica.

--registrar grava o plano; --teste faz uma chamada por provedor, sem integrar a amostra;
--executar exige o plano ja publicado; --sast roda Bandit e Semgrep com regras fixadas.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import analise_principal as analise
import coleta_gemini
import t04_coleta as api
from t04_docker import command

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'dados' / 'coleta-principal'
REGRAS = ROOT / 'regras-sast' / 'semgrep-python.yaml'
SEMENTE = 2026110328
REPETICOES = 10
NIVEIS = ('N0', 'N1', 'N2', 'N3')
TAREFAS = ('T01', 'T02', 'T03', 'T04', 'T05', 'T06', 'T07', 'T08', 'T09', 'T10')
CATALOGO = {'T05': 'T05c'}
BANCO = ('T01', 'T02', 'T06')
V4 = ('T03', 'T04', 'T05')
GEMINI = 'gemini-3.8-flash'
GPT = 'gpt-5.4-mini-2026-03-17'
MODELOS = (GPT, GEMINI)
PARAMETROS = {GPT: {'temperature': 0.7, 'max_completion_tokens': 4000, 'store': False},
              GEMINI: {'temperature': 0.7, 'maxOutputTokens': 4000, 'thinkingConfig': {'thinkingBudget': 0}}}
LIMITE_TOKENS = 4000


class Parada(RuntimeError):
    """Interrompe a coleta sem registrar geracao, para retomada depois de corrigida a causa."""


def imagem_tag(tarefa):
    if tarefa in BANCO:
        return 'tcc-banco-v2:validacao-1'
    return f'tcc-{tarefa.lower()}:grupos-v4' if tarefa in V4 else f'tcc-{tarefa.lower()}:grupos-v3'


def imagem_id(tarefa):
    return subprocess.check_output(['docker', 'image', 'inspect', imagem_tag(tarefa), '--format', '{{.Id}}'], text=True).strip()


def relatorio(tarefa):
    if tarefa in V4:
        return ROOT / f'docs/instrumentos-v4/{tarefa}-validacao-linux.json'
    return ROOT / ('docs' if tarefa in BANCO else 'docs/instrumentos-v3') / f'{tarefa}-validacao-linux.json'


def prompt(tarefa, nivel):
    return coleta_gemini.prompt(CATALOGO.get(tarefa, tarefa), nivel)


def fontes():
    nomes = {'coleta_principal.py', 'analise_principal.py', 'coleta_gemini.py', 'coleta_v2.py', 't04_coleta.py', 't04_docker.py', 'instrumentos_v3/grupos_funcionais.py'}
    for t in TAREFAS:
        r = json.loads(relatorio(t).read_text(encoding='utf-8'))
        nomes.add(str(relatorio(t).relative_to(ROOT)).replace('\\', '/'))
        nomes.update(r['arquivos'])
        nomes.add(f'tarefas/v2/{CATALOGO.get(t, t)}.json' if t != 'T04' else 'tarefas/T04.json')
    return {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in sorted(nomes)}


def versao_ferramentas():
    python = sys.executable
    bandit = subprocess.run([python, '-m', 'bandit', '--version'], capture_output=True, text=True).stdout.splitlines()[0]
    semgrep = subprocess.run([semgrep_exe(), '--version'], capture_output=True, text=True).stdout.strip()
    return dict(bandit=bandit.split()[-1], semgrep=semgrep, regras_semgrep_sha256=hashlib.sha256(REGRAS.read_bytes()).hexdigest())


def semgrep_exe():
    return str(Path(sys.executable).with_name('semgrep.exe' if os.name == 'nt' else 'semgrep'))


def montar_jobs():
    jobs = [dict(tarefa=t, modelo=m, nivel=n, repeticao=r) for t in TAREFAS for m in MODELOS for n in NIVEIS for r in range(1, REPETICOES + 1)]
    random.Random(SEMENTE).shuffle(jobs)
    for i, job in enumerate(jobs, 1):
        job.update(id=f'cp-{i:04d}', prompt=prompt(job['tarefa'], job['nivel']))
    return jobs


def registrar():
    arquivo = DATA / 'plano.json'
    imagens = {t: imagem_id(t) for t in TAREFAS}
    if arquivo.exists():
        plano = json.loads(arquivo.read_text(encoding='utf-8'))
        assert plano['fontes_sha256'] == fontes(), 'Fontes alteradas depois do plano'
        assert plano['imagens'] == imagens, 'Imagem alterada depois do plano'
        assert plano['ferramentas'] == versao_ferramentas(), 'Ferramentas de analise alteradas depois do plano'
        return plano
    for t in TAREFAS:
        r = json.loads(relatorio(t).read_text(encoding='utf-8'))
        assert r['imagem'] == imagens[t], 'Imagem difere da validacao: ' + t
        grupos = [r['referencias'], r['regressao']] if isinstance(r['referencias'], dict) else [r]
        assert all(g['referencias'] == g['expectativas_atendidas'] for g in grupos), t
        assert all(r['probe']['confinamento'].values()), t
    jobs = montar_jobs()
    plano = dict(versao='coleta-principal-1', registrado_em=api.now(), semente_ordem=SEMENTE, semente_revisao=analise.SEMENTE_REVISAO,
                 revisao_manual=analise.amostra_revisao(jobs), jobs=jobs, imagens=imagens, fontes_sha256=fontes(), parametros=PARAMETROS, ferramentas=versao_ferramentas(),
                 regras='Metodologia, subsecao 3.5; analise_principal.py',
                 retentativas='Ate duas tentativas em erro 5xx ou de transporte; erros 4xx interrompem a coleta sem registrar geracao; nenhuma regeneracao por falha funcional, codigo invalido ou truncamento.')
    api.save(arquivo, plano)
    return plano


def plano_publicado():
    """O plano precisa estar no GitHub, com data verificavel, antes da primeira chamada."""
    caminho = 'dados/coleta-principal/plano.json'
    git = ['git', '-c', 'safe.directory=*', '-C', str(ROOT)]
    subprocess.run(git + ['fetch', '-q', 'origin'], check=True)
    if subprocess.run(git + ['cat-file', '-e', f'origin/main:{caminho}'], capture_output=True).returncode:
        raise Parada('Plano ainda nao publicado no GitHub')
    if subprocess.run(git + ['diff', '--quiet', 'origin/main', '--', caminho]).returncode:
        raise Parada('Plano local difere do publicado')


def chave(modelo):
    nome = 'GEMINI_API_KEY' if modelo == GEMINI else 'OPENAI_API_KEY'
    valor = os.environ.get(nome)
    if not valor and os.name == 'nt':
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as registro:
            valor = winreg.QueryValueEx(registro, nome)[0]
    if not valor:
        raise Parada(nome + ' indisponivel')
    return valor


def pedido(modelo, texto, segredo):
    if modelo == GEMINI:
        corpo = {'contents': [{'role': 'user', 'parts': [{'text': texto}]}], 'generationConfig': PARAMETROS[GEMINI]}
        return (f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI}:generateContent', corpo,
                {'x-goog-api-key': segredo, 'Content-Type': 'application/json'})
    corpo = {'model': GPT, 'messages': [{'role': 'user', 'content': texto}], **PARAMETROS[GPT]}
    return 'https://api.openai.com/v1/chat/completions', corpo, {'Authorization': 'Bearer ' + segredo, 'Content-Type': 'application/json'}


def interpretar(modelo, resposta):
    """Devolve texto, motivo de termino, versao informada e erro, em formato comum aos provedores."""
    if modelo == GEMINI:
        texto, motivo, erro = coleta_gemini.interpretar(resposta)
        return texto, motivo, resposta.get('modelVersion'), erro
    escolha = (resposta.get('choices') or [{}])[0]
    texto = (escolha.get('message') or {}).get('content') or ''
    motivo = escolha.get('finish_reason')
    erro = None if motivo == 'stop' and texto.strip() else 'Resposta vazia ou incompleta; nao sera reexecutada para selecionar uma melhor'
    return texto, motivo, resposta.get('model'), erro


def chamar(modelo, texto, tentativas, ao_registrar=lambda: None):
    segredo = chave(modelo)
    url, corpo, cabecalhos = pedido(modelo, texto, segredo)
    resposta = None
    for numero in (1, 2):
        tentativa = dict(numero=numero, iniciada_em=api.now())
        tentativas.append(tentativa)
        ao_registrar()
        try:
            req = urllib.request.Request(url, data=json.dumps(corpo).encode(), headers=cabecalhos, method='POST')
            with urllib.request.urlopen(req, timeout=300) as r:
                tentativa.update(http=r.status, request_id=r.headers.get('x-request-id'))
                resposta = json.load(r)
            break
        except urllib.error.HTTPError as exc:
            detalhe = exc.read().decode(errors='replace').replace(segredo, '[REDACTED]')[:2000]
            tentativa.update(http=exc.code, erro=detalhe)
            if 400 <= exc.code < 500:
                raise Parada(f'{modelo}: HTTP {exc.code}; verificar saldo, cota ou parametros. {detalhe[:300]}') from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            tentativa['erro'] = type(exc).__name__
        finally:
            tentativa['terminada_em'] = api.now()
            ao_registrar()
        if numero == 1:
            time.sleep(5)
    return corpo, resposta


def coletar(job):
    pasta = DATA / job['id']
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / 'geracao.json'
    if arquivo.exists():
        registro = json.loads(arquivo.read_text(encoding='utf-8'))
        if 'concluida_em' not in registro:
            raise Parada(f"Requisicao interrompida em {job['id']}; resultado desconhecido, nao repetir automaticamente")
        return registro
    registro = dict(**job, iniciado_em=api.now(), tentativas=[], resposta=None, erro=None)
    try:
        registro['payload'], registro['resposta'] = chamar(job['modelo'], job['prompt'], registro['tentativas'], lambda: api.save(arquivo, registro))
    except Parada:
        # A chamada foi recusada e nao constitui resultado; a tentativa fica no registro de recusas.
        with (DATA / 'chamadas-recusadas.jsonl').open('a', encoding='utf-8') as log:
            log.write(json.dumps(dict(id=job['id'], em=api.now(), tentativas=registro['tentativas']), ensure_ascii=False) + '\n')
        arquivo.unlink(missing_ok=True)
        raise
    if registro['resposta'] is None:
        registro['erro'] = 'Nenhuma resposta de geracao; consultar tentativas'
    else:
        texto, registro['finish_reason'], versao, registro['erro'] = interpretar(job['modelo'], registro['resposta'])
        registro['versao_informada'] = versao
        if versao != job['modelo']:
            registro['concluida_em'] = api.now()
            api.save(arquivo, registro)
            raise Parada(f"Versao inesperada em {job['id']}: {versao}")
        if not registro['erro']:
            codigo = api.extract(texto)
            (pasta / 'amostra.py').write_bytes(codigo.encode())
            registro['codigo_sha256'] = hashlib.sha256(codigo.encode()).hexdigest()
            try:
                ast.parse(codigo)
            except SyntaxError:
                registro['erro'] = 'SyntaxError no codigo retornado'
    registro['concluida_em'] = api.now()
    api.save(arquivo, registro)
    return registro


def avaliar_docker(tarefa, imagem, amostra):
    args = (['--tarefa', tarefa] if tarefa in BANCO else []) + ['--amostra', '/candidate/amostra.py']
    nome = 'tcc-cp-' + uuid.uuid4().hex[:12]
    try:
        p = subprocess.run(command(imagem, nome, args, amostra), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=240)
        linhas = [l.split(':', 1)[1] for l in p.stdout.splitlines() if l.startswith('TCC_RESULTADO_JSON:')]
        r = json.loads(linhas[-1]) if linhas else dict(estado='inconclusivo', erro='Executor sem resultado', testes=[])
        r.update(imagem=imagem, container_exit=p.returncode, stdout=p.stdout[-4000:], stderr=p.stderr[-4000:])
        return r
    except subprocess.TimeoutExpired:
        return dict(imagem=imagem, estado='inconclusivo', erro='Timeout do conteiner', testes=[])
    finally:
        subprocess.run(['docker', 'rm', '-f', nome], capture_output=True, timeout=30)


def executar(limite=None):
    plano = registrar()
    plano_publicado()
    feitas = 0
    for job in plano['jobs']:
        if limite is not None and feitas >= limite:
            break
        registro = coletar(job)
        pasta = DATA / job['id']
        saida = pasta / 'avaliacao.json'
        if saida.exists():
            continue
        assert imagem_id(job['tarefa']) == plano['imagens'][job['tarefa']], 'Imagem alterada durante a coleta'
        sem_codigo = registro['erro'] or not (pasta / 'amostra.py').exists()
        resultado = dict(estado='inconclusivo', erro=registro['erro'], testes=[]) if sem_codigo else avaliar_docker(job['tarefa'], plano['imagens'][job['tarefa']], pasta / 'amostra.py')
        api.save(saida, resultado)
        feitas += 1
        print(job['id'], job['tarefa'], job['modelo'][:6], job['nivel'], analise.desfecho_seguranca(job['tarefa'], resultado), analise.desfecho_funcional(resultado, job['nivel'])[0], str(registro['erro'] or '')[:60], flush=True)
    faltam = [j['id'] for j in plano['jobs'] if not (DATA / j['id'] / 'avaliacao.json').exists()]
    print('Faltam', len(faltam), 'geracoes', flush=True)


def sast():
    plano = registrar()
    faltam = [j['id'] for j in plano['jobs'] if not (DATA / j['id'] / 'avaliacao.json').exists()]
    if faltam:
        raise Parada(f'{len(faltam)} geracoes pendentes; rodar a analise estatica ao final')
    alvos = [f"{j['id']}/amostra.py" for j in plano['jobs'] if (DATA / j['id'] / 'amostra.py').exists()]
    destino = DATA / 'sast'
    destino.mkdir(exist_ok=True)
    ambiente = {**os.environ, 'PYTHONUTF8': '1'}
    bandit = subprocess.run([sys.executable, '-m', 'bandit', '-f', 'json', '-q', *alvos], cwd=DATA, capture_output=True, text=True, encoding='utf-8', errors='replace', env=ambiente)
    if bandit.returncode not in (0, 1) or not bandit.stdout.strip():
        raise RuntimeError('Bandit falhou: ' + bandit.stderr[-500:])
    (destino / 'bandit.json').write_text(bandit.stdout, encoding='utf-8')
    semgrep = subprocess.run([semgrep_exe(), 'scan', '--config', str(REGRAS), '--json', '--metrics=off', '--disable-version-check', '--quiet', '--no-git-ignore', *alvos],
                             cwd=DATA, capture_output=True, text=True, encoding='utf-8', errors='replace', env=ambiente)
    if semgrep.returncode not in (0, 1) or not semgrep.stdout.strip():
        raise RuntimeError('Semgrep falhou: ' + semgrep.stderr[-500:])
    (destino / 'semgrep.json').write_text(semgrep.stdout, encoding='utf-8')
    b, s = json.loads(bandit.stdout), json.loads(semgrep.stdout)
    print('Bandit:', len(b['results']), 'achados;', len(b.get('errors', [])), 'erros | Semgrep:', len(s['results']), 'achados;', len(s['errors']), 'erros;', len(alvos), 'alvos')


def teste():
    """Uma chamada por provedor com um prompt real; nao integra a amostra."""
    saida = {}
    for modelo in MODELOS:
        tentativas = []
        _, resposta = chamar(modelo, prompt('T08', 'N3'), tentativas)
        if resposta is None:
            raise Parada(f'{modelo}: sem resposta. {tentativas}')
        texto, motivo, versao, erro = interpretar(modelo, resposta)
        uso = resposta.get('usage') or resposta.get('usageMetadata')
        saida[modelo] = dict(versao_informada=versao, motivo=motivo, erro=erro, caracteres=len(texto), uso=uso)
        print(modelo, json.dumps(saida[modelo], ensure_ascii=False), flush=True)
        if versao != modelo or erro:
            raise Parada(f'{modelo}: teste reprovado')
    return saida


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--registrar', action='store_true')
    p.add_argument('--teste', action='store_true')
    p.add_argument('--executar', action='store_true')
    p.add_argument('--limite', type=int, help='maximo de geracoes novas nesta execucao')
    p.add_argument('--sast', action='store_true')
    args = p.parse_args()
    try:
        if args.teste:
            teste()
        if args.registrar:
            print('Plano:', len(registrar()['jobs']), 'geracoes', flush=True)
        if args.executar:
            executar(args.limite)
        if args.sast:
            sast()
    except Parada as exc:
        print('PARADA:', exc, flush=True)
        sys.exit(3)


if __name__ == '__main__':
    main()
