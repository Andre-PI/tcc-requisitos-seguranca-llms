"""Coleta exploratoria do gemini-3.8-flash nas dez tarefas, separada das demais coletas."""
import argparse
import ast
from collections import Counter
import hashlib
import importlib
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
import coleta_v2
import t04_coleta as api
from t04_docker import command

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'dados' / 'gemini-exploratoria'
MODELO = 'gemini-3.8-flash'
URL = f'https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent'
SEMENTE = 2026110327
NIVEIS = ('N0', 'N1', 'N2', 'N3')
PARAMETROS = {'temperature': 0.7, 'maxOutputTokens': 4000, 'thinkingConfig': {'thinkingBudget': 0}}
# Instrumento mais recente de cada tarefa: v3 onde ha grupos funcionais; v2 nas demais.
V3 = ('T03', 'T04', 'T07', 'T08', 'T09', 'T10')
V2 = {'T01': 't01_docker', 'T02': 't02_docker', 'T05c': 't05c_docker', 'T06': 't06_docker'}
TAREFAS = ('T01', 'T02', 'T03', 'T04', 'T05c', 'T06', 'T07', 'T08', 'T09', 'T10')


class Parada(RuntimeError):
    """Condicao que interrompe a coleta sem registrar geracao."""


def relatorio(tarefa):
    return ROOT / ('docs/instrumentos-v3' if tarefa in V3 else 'docs') / f'{tarefa}-validacao-linux.json'


def prompt(tarefa, nivel):
    return api.montar_prompt(nivel) if tarefa == 'T04' else coleta_v2.montar_prompt(tarefa, nivel)


def imagem_atual(tarefa):
    if tarefa in V2:
        return importlib.import_module(V2[tarefa]).image_id()
    return subprocess.check_output(['docker', 'image', 'inspect', f'tcc-{tarefa.lower()}:grupos-v3', '--format', '{{.Id}}'], text=True).strip()


def fontes():
    nomes = {'coleta_gemini.py', 'coleta_v2.py', 't04_coleta.py', 't04_docker.py'}
    for tarefa in TAREFAS:
        nomes.add(str(relatorio(tarefa).relative_to(ROOT)).replace('\\', '/'))
        nomes.update(json.loads(relatorio(tarefa).read_text(encoding='utf-8'))['arquivos'])
    return {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in sorted(nomes)}


def registrar_plano():
    arquivo = DATA / 'plano.json'
    imagens = {t: imagem_atual(t) for t in TAREFAS}
    if arquivo.exists():
        plano = json.loads(arquivo.read_text(encoding='utf-8'))
        assert plano['fontes_sha256'] == fontes(), 'Fontes alteradas depois do plano'
        assert plano['imagens'] == imagens, 'Imagem alterada depois do plano'
        return plano
    for tarefa in TAREFAS:
        r = json.loads(relatorio(tarefa).read_text(encoding='utf-8'))
        assert r['imagem'] == imagens[tarefa], 'Imagem difere da validacao: ' + tarefa
        grupos = [r['referencias'], r['regressao']] if tarefa in V3 else [r]
        assert all(g['referencias'] == g['expectativas_atendidas'] for g in grupos), tarefa
        assert all(r['probe']['confinamento'].values()), tarefa
    jobs = [dict(tarefa=t, modelo=MODELO, nivel=n, repeticao=1) for t in TAREFAS for n in NIVEIS]
    random.Random(SEMENTE).shuffle(jobs)
    for i, job in enumerate(jobs, 1):
        job.update(id=f'gem-{i:02d}', prompt=prompt(job['tarefa'], job['nivel']))
    plano = dict(versao='gemini-exploratoria-1', registrado_em=api.now(),
                 natureza='Exploratoria; uma geracao por tarefa e nivel; fora do piloto, das demais coletas e das 800 geracoes principais',
                 semente_ordem=SEMENTE, jobs=jobs, imagens=imagens, fontes_sha256=fontes(), parametros=PARAMETROS,
                 retentativas='Ate duas tentativas em erro 5xx ou de transporte; 429 interrompe a coleta sem registrar geracao; nenhuma regeneracao por falha funcional, codigo invalido ou truncamento.')
    api.save(arquivo, plano)
    return plano


def chave():
    valor = os.environ.get('GEMINI_API_KEY')
    if not valor and os.name == 'nt':
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as registro:
            valor = winreg.QueryValueEx(registro, 'GEMINI_API_KEY')[0]
    if not valor:
        raise RuntimeError('GEMINI_API_KEY indisponivel; nao enviar chave no chat')
    return valor


def interpretar(resposta):
    """Devolve texto, motivo de termino e erro de uma resposta generateContent."""
    candidatos = resposta.get('candidates') or []
    if not candidatos:
        return '', None, 'Resposta sem candidatos'
    motivo = candidatos[0].get('finishReason')
    partes = (candidatos[0].get('content') or {}).get('parts') or []
    texto = ''.join(p.get('text', '') for p in partes if not p.get('thought'))
    if motivo != 'STOP' or not texto.strip():
        return texto, motivo, 'Resposta vazia ou incompleta; nao sera reexecutada para selecionar uma melhor'
    return texto, motivo, None


def coletar(job, plano):
    pasta = DATA / job['id']
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / 'geracao.json'
    if arquivo.exists():
        registro = json.loads(arquivo.read_text(encoding='utf-8'))
        if 'concluida_em' not in registro:
            raise Parada(f"Requisicao interrompida em {job['id']}; resultado desconhecido, nao repetir automaticamente")
        return registro
    segredo = chave()
    payload = {'contents': [{'role': 'user', 'parts': [{'text': job['prompt']}]}], 'generationConfig': plano['parametros']}
    registro = dict(**job, iniciado_em=api.now(), payload=payload, tentativas=[], resposta=None, erro=None)
    for numero in (1, 2):
        tentativa = dict(numero=numero, iniciada_em=api.now())
        registro['tentativas'].append(tentativa)
        api.save(arquivo, registro)
        try:
            pedido = urllib.request.Request(URL, data=json.dumps(payload).encode(), headers={'x-goog-api-key': segredo, 'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(pedido, timeout=300) as r:
                tentativa['http'] = r.status
                registro['resposta'] = json.load(r)
            break
        except urllib.error.HTTPError as exc:
            detalhe = exc.read().decode(errors='replace').replace(segredo, '[REDACTED]')[:2000]
            tentativa.update(http=exc.code, erro=detalhe)
            if exc.code == 429:
                # Saldo ou cota: a chamada nao foi processada e nao constitui resultado da geracao.
                with (DATA / 'chamadas-recusadas.jsonl').open('a', encoding='utf-8') as log:
                    log.write(json.dumps(dict(id=job['id'], em=api.now(), http=429, detalhe=detalhe), ensure_ascii=False) + '\n')
                arquivo.unlink()
                raise Parada('429 recebido: verificar saldo ou cota e retomar depois; nenhuma geracao registrada') from None
            if exc.code not in (500, 502, 503, 504):
                break
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            tentativa['erro'] = type(exc).__name__
        finally:
            tentativa['terminada_em'] = api.now()
            if arquivo.exists():
                api.save(arquivo, registro)
        if numero == 1:
            time.sleep(5)
    if registro['resposta'] is None:
        registro['erro'] = 'Nenhuma resposta de geracao; consultar tentativas'
    else:
        versao = registro['resposta'].get('modelVersion')
        if versao != MODELO:
            registro['erro'] = f'Versao inesperada: {versao}'
            registro['concluida_em'] = api.now()
            api.save(arquivo, registro)
            raise Parada(registro['erro'])
        texto, registro['finish_reason'], registro['erro'] = interpretar(registro['resposta'])
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


def executar_docker(tarefa, imagem, amostra):
    args = ['--amostra', '/candidate/amostra.py']
    if tarefa in V2:
        return importlib.import_module(V2[tarefa]).run(args, amostra)
    nome = f'tcc-gemini-{uuid.uuid4().hex[:12]}'
    try:
        p = subprocess.run(command(imagem, nome, args, amostra), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
        linhas = [l.split(':', 1)[1] for l in p.stdout.splitlines() if l.startswith('TCC_RESULTADO_JSON:')]
        r = json.loads(linhas[-1]) if linhas else dict(estado='inconclusivo', erro='Executor sem resultado', testes=[])
        r.update(imagem=imagem, container_exit=p.returncode, stdout=p.stdout, stderr=p.stderr)
        return r
    except subprocess.TimeoutExpired:
        return dict(imagem=imagem, estado='inconclusivo', erro='Timeout do conteiner', testes=[])
    finally:
        subprocess.run(['docker', 'rm', '-f', nome], capture_output=True, timeout=15)


def resumir(job, registro, resultado):
    from importlib import util
    spec = util.spec_from_file_location('grupos_funcionais', ROOT / 'instrumentos_v3/grupos_funcionais.py')
    grupos = util.module_from_spec(spec)
    spec.loader.exec_module(grupos)
    testes = resultado.get('testes', [])
    if 'grupos_funcionais' in resultado:
        funcional = grupos.resultado_funcional(resultado, job['nivel'])['status']
    else:
        casos = [t['status'] for t in testes if t['tipo'] == 'funcional']
        funcional = 'inconclusivo' if not casos else 'aprovado' if all(s == 'aprovado' for s in casos) else 'reprovado'
    uso = (registro.get('resposta') or {}).get('usageMetadata') or {}
    contagem = Counter(t['status'] for t in testes if t['tipo'].startswith('seguranca') or t['tipo'] == 'argumentos')
    return dict(id=job['id'], tarefa=job['tarefa'], nivel=job['nivel'], funcional=funcional, seguranca=dict(contagem),
                reprovados=[t['teste'] for t in testes if t['status'] in ('reprovado', 'exposicao', 'acesso_externo_observado') and t['tipo'] != 'funcional'],
                erro=registro['erro'] or resultado.get('erro'), finish_reason=registro.get('finish_reason'),
                entrada=uso.get('promptTokenCount'), saida=uso.get('candidatesTokenCount'), raciocinio=uso.get('thoughtsTokenCount'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--executar', action='store_true', help='faz ate 40 geracoes pagas e avalia no Docker')
    args = p.parse_args()
    plano = registrar_plano()
    print('Plano registrado:', len(plano['jobs']), 'geracoes', flush=True)
    if not args.executar:
        return
    linhas = []
    try:
        for job in plano['jobs']:
            registro = coletar(job, plano)
            pasta = DATA / job['id']
            saida = pasta / 'avaliacao.json'
            if not saida.exists():
                assert imagem_atual(job['tarefa']) == plano['imagens'][job['tarefa']]
                sem_codigo = registro['erro'] or not (pasta / 'amostra.py').exists()
                resultado = dict(estado='inconclusivo', erro=registro['erro'], testes=[]) if sem_codigo else executar_docker(job['tarefa'], plano['imagens'][job['tarefa']], pasta / 'amostra.py')
                api.save(saida, resultado)
            linha = resumir(job, registro, json.loads(saida.read_text(encoding='utf-8')))
            linhas.append(linha)
            print(json.dumps(linha, ensure_ascii=False), flush=True)
    except Parada as exc:
        print('PARADA:', exc, flush=True)
        sys.exit(3)
    api.save(DATA / 'resumo.json', dict(plano='plano.json', amostras=linhas, encerrado_em=api.now()))


if __name__ == '__main__':
    main()
