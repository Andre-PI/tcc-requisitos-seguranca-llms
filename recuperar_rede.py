"""Emenda 01: refaz somente as geracoes sem resposta por falha de rede.

--registrar move os registros para falhas-de-rede/ e grava a emenda, a publicar antes de refazer.
--executar refaz as geracoes da emenda e para, sem registrar nada, se a rede falhar de novo.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import coleta_principal as c

DATA = c.DATA
EMENDA = DATA / 'emenda-01-rede.json'
ARQUIVO = DATA / 'falhas-de-rede'


def sem_resposta(jobs):
    """Geracoes concluidas sem nenhuma resposta do provedor e com falha de transporte em todas as tentativas."""
    ids = []
    for job in jobs:
        arquivo = DATA / job['id'] / 'geracao.json'
        if not arquivo.exists():
            continue
        r = json.loads(arquivo.read_text(encoding='utf-8'))
        transporte = r['tentativas'] and all('http' not in t and t.get('erro') for t in r['tentativas'])
        if 'concluida_em' in r and r.get('resposta') is None and transporte:
            ids.append(job['id'])
    return ids


def pendentes(jobs):
    return [j['id'] for j in jobs if not (DATA / j['id'] / 'avaliacao.json').exists()]


def registrar():
    assert not EMENDA.exists(), 'Emenda ja registrada'
    jobs = c.registrar()['jobs']
    assert not pendentes(jobs), 'A coleta ainda nao terminou'
    ids = sem_resposta(jobs)
    falhas = []
    for gid in ids:
        r = json.loads((DATA / gid / 'geracao.json').read_text(encoding='utf-8'))
        falhas.append(dict(id=gid, tarefa=r['tarefa'], modelo=r['modelo'], nivel=r['nivel'], repeticao=r['repeticao'], iniciado_em=r['iniciado_em'], tentativas=r['tentativas']))
    ARQUIVO.mkdir(exist_ok=True)
    for gid in ids:
        shutil.move(str(DATA / gid), str(ARQUIVO / gid))
    c.api.save(EMENDA, dict(versao='emenda-01', registrada_em=c.api.now(), tipo='Desvio do plano',
                            motivo='Queda de internet durante a coleta. O executor registrou como concluidas geracoes sem resposta do provedor, em vez de interromper a coleta.',
                            tratamento='Registros preservados em falhas-de-rede/. As geracoes sao refeitas com os mesmos prompts e parametros, fora da ordem sorteada. Nenhuma geracao com resposta do provedor e refeita.',
                            geracoes=falhas))
    print(len(ids), 'geracoes movidas; publicar a emenda antes de refazer')


def chamar_sem_registrar_falha(chamar):
    """Sem resposta do provedor, interrompe em vez de registrar a geracao como concluida."""
    def envolvida(modelo, texto, tentativas, ao_registrar=lambda: None):
        corpo, resposta = chamar(modelo, texto, tentativas, ao_registrar)
        if resposta is None:
            raise c.Parada('Sem resposta do provedor; verificar a rede e retomar')
        return corpo, resposta
    return envolvida


def executar():
    emenda = json.loads(EMENDA.read_text(encoding='utf-8'))
    esperadas = {g['id'] for g in emenda['geracoes']}
    jobs = c.registrar()['jobs']
    assert set(pendentes(jobs)) <= esperadas, 'Ha geracoes pendentes fora da emenda'
    c.chamar = chamar_sem_registrar_falha(c.chamar)
    c.executar()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--registrar', action='store_true')
    p.add_argument('--executar', action='store_true')
    args = p.parse_args()
    try:
        if args.registrar:
            registrar()
        if args.executar:
            executar()
    except c.Parada as exc:
        print('PARADA:', exc, flush=True)
        sys.exit(3)


if __name__ == '__main__':
    main()
