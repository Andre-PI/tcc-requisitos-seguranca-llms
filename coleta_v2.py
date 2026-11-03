"""Coleta exploratoria com o contrato comum v2, separada das coletas anteriores."""
import argparse
from collections import Counter
import hashlib
import importlib
import json
from pathlib import Path
import random
import re
import t04_coleta as api

ROOT = Path(__file__).resolve().parent
NIVEIS = ('N0', 'N1', 'N2', 'N3')
TAREFAS = {
    'T07': dict(docker='t07_docker', referencias=10, semente=2026110317,
                fontes=['t07_utilitario.py', 't07_verificador.py', 't07_referencias.py', 't07_worker_linux.py', 't07_docker.py',
                        'docker/t07/Dockerfile', 'docker/t07/requirements.txt', 'docs/T07-protocolo.md']),
}


def montar_prompt(tarefa, nivel):
    c = json.loads((ROOT / f'tarefas/v2/{tarefa}.json').read_text(encoding='utf-8'))
    if nivel not in NIVEIS:
        raise ValueError(nivel)
    corpo = c['N0'] if nivel == 'N0' else c['N1']
    if nivel in ('N2', 'N3'):
        corpo += ' ' + c[nivel + '_extra']
    return '\n\n'.join([corpo, c['contrato_comum'], c['sufixo']])


def fontes(tarefa):
    nomes = TAREFAS[tarefa]['fontes'] + [f'tarefas/v2/{tarefa}.json', 'docs/contrato-comum-v2.md', 'coleta_v2.py', 't04_coleta.py', 't04_docker.py']
    return {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in nomes}


def registrar_plano(tarefa, pasta, imagem):
    arquivo = pasta / 'plano.json'
    if arquivo.exists():
        plano = json.loads(arquivo.read_text(encoding='utf-8'))
        assert plano['fontes_sha256'] == fontes(tarefa), 'Fontes alteradas depois do plano'
        assert plano['imagem'] == imagem, 'Imagem alterada depois do plano'
        return plano
    cfg = TAREFAS[tarefa]
    validacao = json.loads((ROOT / f'docs/{tarefa}-validacao-linux.json').read_text(encoding='utf-8'))
    assert validacao['referencias'] == validacao['expectativas_atendidas'] == cfg['referencias']
    assert validacao['imagem'] == imagem and all(validacao['probe']['confinamento'].values())
    jobs = [dict(modelo=m, nivel=n, repeticao=1) for m in api.MODELS for n in NIVEIS]
    random.Random(cfg['semente']).shuffle(jobs)
    for i, job in enumerate(jobs, 1):
        job.update(id=f'{tarefa.lower()}v2-{i:02d}', prompt=montar_prompt(tarefa, job['nivel']))
    plano = dict(versao=f'{tarefa.lower()}-exploratoria-v2', registrado_em=api.now(),
                 natureza='Exploratoria; contrato comum v2; fora do piloto, da coleta v1 e das 800 geracoes principais',
                 semente_ordem=cfg['semente'], jobs=jobs, imagem=imagem, fontes_sha256=fontes(tarefa),
                 parametros={'temperature': 0.7, 'max_completion_tokens': 1500, 'store': False},
                 retentativas='Ate duas tentativas em erro transitorio; nenhuma regeneracao por falha funcional, codigo invalido ou truncamento.')
    api.save(arquivo, plano)
    return plano


def resumir(registro, resultado, codigo=''):
    testes = resultado.get('testes', [])
    funcionais = [t for t in testes if t['tipo'] == 'funcional']
    estado = 'inconclusivo' if not funcionais else 'aprovado' if all(t['status'] == 'aprovado' for t in funcionais) else 'reprovado'
    grupos = {}
    for t in testes:
        if t['tipo'] != 'funcional':
            grupos.setdefault(t['tipo'], Counter())[t['status']] += 1
    return dict(id=registro['id'], modelo=registro['modelo'], nivel=registro['nivel'], funcional=estado,
                grupos={k: dict(v) for k, v in grupos.items()}, erro=registro['erro'] or resultado.get('erro'),
                usa_delimitador=bool(re.search(r"""['"]--['"]""", codigo)), shell_true=bool(re.search(r'shell\s*=\s*True', codigo)),
                uso=(registro['resposta'] or {}).get('usage', {}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('tarefa', choices=sorted(TAREFAS))
    p.add_argument('--executar', action='store_true', help='faz ate oito geracoes pagas e avalia no Docker')
    args = p.parse_args()
    docker = importlib.import_module(TAREFAS[args.tarefa]['docker'])
    pasta = ROOT / f'dados/{args.tarefa.lower()}-exploratoria-v2'
    plano = registrar_plano(args.tarefa, pasta, docker.image_id())
    print('Plano registrado:', len(plano['jobs']), 'geracoes; imagem', plano['imagem'], flush=True)
    if not args.executar:
        return
    api.DATA = pasta
    linhas = []
    for job in plano['jobs']:
        registro = api.collect(job, plano)
        item = pasta / job['id']
        saida = item / 'avaliacao.json'
        if not saida.exists():
            assert docker.image_id() == plano['imagem']
            resultado = dict(estado='inconclusivo', erro=registro['erro'], testes=[]) if registro['erro'] else docker.run(['--amostra', '/candidate/amostra.py'], item / 'amostra.py')
            api.save(saida, resultado)
        resultado = json.loads(saida.read_text(encoding='utf-8'))
        fonte = item / 'amostra.py'
        linha = resumir(registro, resultado, fonte.read_text(encoding='utf-8') if fonte.exists() else '')
        linhas.append(linha)
        print(job['id'], job['modelo'], job['nivel'], 'funcional=' + linha['funcional'], json.dumps(linha['grupos']), 'delimitador=' + str(linha['usa_delimitador']), flush=True)
    api.save(pasta / 'resumo.json', dict(plano='plano.json', amostras=linhas, encerrado_em=api.now()))


if __name__ == '__main__':
    main()
