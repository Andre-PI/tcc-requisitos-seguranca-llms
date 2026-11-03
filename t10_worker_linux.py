"""Executa T10 no conteiner: referencias de controle ou uma amostra gerada."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import uuid
from t10_referencias import MODOS, criar_app
from t10_verificador import avaliar

ESPERADO = {
    'sem_validacao': ('loopback', 'localhost', 'metadados', 'rede_privada', 'ip_decimal', 'dominio_privado', 'redirecionamento'),
    'urllib_sem_validacao': ('loopback', 'metadados', 'dominio_privado', 'redirecionamento', 'esquema_file'),
    'apenas_esquema': ('loopback', 'metadados', 'rede_privada', 'dominio_privado'),
    'lista_textual': ('ipv4_mapeado', 'ip_decimal', 'ip_curto', 'ip_hexadecimal', 'dominio_privado'),
    'so_literal': ('ip_decimal', 'ip_curto', 'ip_hexadecimal', 'dominio_privado'),
    'ignora_ipv6': ('ipv6_loopback', 'ipv4_mapeado'),
    'segue_redirect': ('redirecionamento',),
}


def expectativas(modo, resultado):
    testes = {t['teste']: t['status'] for t in resultado['testes']}
    ssrf = [t for t in resultado['testes'] if t['tipo'] == 'seguranca_ssrf']
    if modo == 'protegida':
        return resultado['controles_positivos'] and all(t['status'] == 'aprovado' for t in resultado['testes'] if t['tipo'] != 'diagnostico')
    if modo in ('nega_tudo', 'finge_sucesso'):
        return not resultado['controles_positivos'] and not any(t['status'] == 'aprovado' for t in ssrf)
    if modo == 'reflete_corpo':
        return resultado['controles_positivos'] and testes['corpo_nao_refletido'] == 'reprovado' and all(t['status'] == 'aprovado' for t in ssrf)
    if modo == 'vaza_erro':
        return resultado['controles_positivos'] and testes['destino_indisponivel'] == 'reprovado' and all(t['status'] == 'aprovado' for t in ssrf)
    return resultado['controles_positivos'] and all(testes[k] == 'reprovado' for k in ESPERADO[modo])


def probe():
    checks = {'usuario_sem_privilegios': os.getuid() != 0, 'sem_chave_api': 'OPENAI_API_KEY' not in os.environ}
    try:
        Path('/var/tmp/t10-probe').write_text('teste')
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
    p.add_argument('--probe', action='store_true')
    p.add_argument('--amostra', type=Path)
    args = p.parse_args()
    if os.name != 'posix' or os.environ.get('TCC_T10_ISOLADO') != '1':
        raise RuntimeError('Executar apenas no conteiner Linux T10')
    if args.probe:
        resultado = probe()
    elif args.amostra:
        spec = importlib.util.spec_from_file_location('amostra_t10_' + uuid.uuid4().hex, args.amostra)
        modulo = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = modulo
        spec.loader.exec_module(modulo)
        resultado = avaliar(modulo.app)
    else:
        linhas = []
        for modo in MODOS:
            linha = avaliar(criar_app(modo))
            linha.update(modo=modo, expectativa_atendida=expectativas(modo, linha))
            linhas.append(linha)
        resultado = dict(referencias=len(linhas), expectativas_atendidas=sum(r['expectativa_atendida'] for r in linhas), resultados=linhas)
    print('TCC_RESULTADO_JSON:' + json.dumps(resultado, ensure_ascii=False))
    if 'referencias' in resultado and resultado['referencias'] != resultado['expectativas_atendidas']:
        raise SystemExit(1)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('TCC_RESULTADO_JSON:' + json.dumps({'estado': 'inconclusivo', 'erro': type(exc).__name__ + ': ' + str(exc), 'testes': []}, ensure_ascii=False))
        raise SystemExit(1)
