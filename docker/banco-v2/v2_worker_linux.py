"""Executa T01, T02 ou T06 no conteiner: referencias de controle ou uma amostra gerada."""
import argparse
import importlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import uuid
import v2_banco


def probe():
    checks = {'usuario_sem_privilegios': os.getuid() != 0, 'sem_chave_api': 'OPENAI_API_KEY' not in os.environ}
    try:
        Path('/var/tmp/v2-probe').write_text('teste')
        checks['raiz_somente_leitura'] = False
    except OSError:
        checks['raiz_somente_leitura'] = True
    try:
        with socket.create_connection(('1.1.1.1', 443), timeout=2):
            checks['rede_bloqueada'] = False
    except OSError:
        checks['rede_bloqueada'] = True
    return dict(confinamento=checks, python=sys.version)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--tarefa', required=True, choices=('T01', 'T02', 'T06'))
    p.add_argument('--probe', action='store_true')
    p.add_argument('--amostra', type=Path)
    args = p.parse_args()
    if os.name != 'posix' or os.environ.get('TCC_BANCO_ISOLADO') != '1':
        raise RuntimeError('Executar apenas no conteiner Linux')
    if args.probe:
        return probe()
    t = args.tarefa.lower()
    verificador = importlib.import_module(t + '_verificador')
    if args.amostra:
        with v2_banco.banco(verificador.ESQUEMA) as caminho:
            verificador.preparar()
            spec = importlib.util.spec_from_file_location('amostra_' + uuid.uuid4().hex, args.amostra)
            modulo = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = modulo
            spec.loader.exec_module(modulo)
            return verificador.avaliar(modulo.app, caminho, args.amostra.read_text(encoding='utf-8'))
    referencias = importlib.import_module(t + '_referencias')
    linhas = []
    for modo in referencias.MODOS:
        with v2_banco.banco(verificador.ESQUEMA) as caminho:
            verificador.preparar()
            linha = verificador.avaliar(referencias.criar_app(modo), caminho, referencias.fonte(modo))
        linha.update(modo=modo, expectativa_atendida=referencias.expectativas(modo, linha))
        linhas.append(linha)
    return dict(referencias=len(linhas), expectativas_atendidas=sum(r['expectativa_atendida'] for r in linhas), resultados=linhas)


if __name__ == '__main__':
    try:
        resultado = main()
    except Exception as exc:
        print('TCC_RESULTADO_JSON:' + json.dumps({'estado': 'inconclusivo', 'erro': type(exc).__name__ + ': ' + str(exc), 'testes': []}, ensure_ascii=False))
        raise SystemExit(1)
    print('TCC_RESULTADO_JSON:' + json.dumps(resultado, ensure_ascii=False))
    if 'referencias' in resultado and resultado['referencias'] != resultado['expectativas_atendidas']:
        raise SystemExit(1)
