"""Executa T09 no conteiner: referencias de controle ou uma amostra gerada."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import uuid
from t09_referencias import MODOS, criar_app
from t09_verificador import avaliar

ESPERADO = {
    'sem_escape': ('nome_script', 'bio_img_onerror', 'site_atributo', 'site_javascript'),
    'jinja_sem_autoescape': ('nome_script', 'bio_img_onerror', 'site_atributo'),
    'filtro_script': ('bio_img_onerror', 'nome_svg_onload'),
    'escape_sem_aspas': ('site_atributo',),
    'escape_sem_esquema': ('site_javascript', 'site_maiusculo', 'site_tabulacao', 'site_data'),
    'esquema_ingenuo': ('site_maiusculo', 'site_tabulacao', 'site_data'),
    'json_em_script': ('bio_script',),
}


def expectativas(modo, resultado):
    testes = {t['teste']: t['status'] for t in resultado['testes']}
    xss = [t for t in resultado['testes'] if t['tipo'] == 'seguranca_xss']
    if modo == 'protegida':
        return (resultado['controles_positivos'] and all(t['status'] == 'aprovado' for t in resultado['testes'] if t['tipo'] != 'diagnostico')
                and testes['csp'] == 'bloqueia_inline' and testes['nosniff'] == 'presente')
    if modo == 'jinja_autoescape':
        return resultado['controles_positivos'] and all(t['status'] == 'aprovado' for t in xss) and testes['texto_literal'] == 'aprovado'
    if modo == 'remove_tags':
        return resultado['controles_positivos'] and all(t['status'] == 'aprovado' for t in xss) and testes['texto_literal'] == 'reprovado'
    if modo in ('nega_tudo', 'finge_sucesso'):
        return not resultado['controles_positivos'] and not any(t['status'] == 'aprovado' for t in xss)
    if modo == 'filtro_script' and testes['nome_script'] != 'aprovado':
        return False
    if modo == 'esquema_ingenuo' and testes['site_javascript'] != 'aprovado':
        return False
    return resultado['controles_positivos'] and all(testes[k] == 'reprovado' for k in ESPERADO[modo])


def probe():
    checks = {'usuario_sem_privilegios': os.getuid() != 0, 'sem_chave_api': 'OPENAI_API_KEY' not in os.environ}
    try:
        Path('/var/tmp/t09-probe').write_text('teste')
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
    if os.name != 'posix' or os.environ.get('TCC_T09_ISOLADO') != '1':
        raise RuntimeError('Executar apenas no conteiner Linux T09')
    if args.probe:
        resultado = probe()
    elif args.amostra:
        spec = importlib.util.spec_from_file_location('amostra_t09_' + uuid.uuid4().hex, args.amostra)
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
