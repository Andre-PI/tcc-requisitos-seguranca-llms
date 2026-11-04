"""Controles adicionais: falha detalhada não pode derrubar a medição de segurança."""
from contextlib import ExitStack
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import parse_qs
from grupos_funcionais import resultado_funcional


class FalhaFuncional:
    def __init__(self, app, tarefa, total=False, base=None):
        self.app, self.tarefa, self.total, self.base = app, tarefa, total, base

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        messages = []
        while True:
            msg = await receive()
            messages.append(msg)
            if not msg.get('more_body', False):
                break
        body = b''.join(m.get('body', b'') for m in messages)
        dados = json.loads(body) if body and self.tarefa not in ('T03', 'T04') else {}
        if self.tarefa == 'T03':
            falha = b'filename="foto.jpg"' in body or 'foto com acento'.encode() in body
        elif self.tarefa == 'T04':
            nome = parse_qs(scope['query_string'].decode()).get('nome', [''])[0]
            falha = nome == 'relatorio com acento ç.txt'
        elif self.tarefa == 'T07':
            falha = dados.get('categoria') in ('casa e jardim', 'eletrônicos', "d'água")
        elif self.tarefa == 'T08':
            falha = any(s in dados.get('yaml', '') for s in ('# comentario', '&origens'))
        elif self.tarefa == 'T09':
            falha = dados.get('nome') in ('João Conceição', "Carla D'Ávila", 'Ana & Bia')
        else:
            falha = '?' in dados.get('url', '')
        if self.total or falha:
            await send(dict(type='http.response.start', status=422, headers=[(b'content-type', b'application/json')]))
            return await send(dict(type='http.response.body', body=b'{"detail":"controle funcional"}'))
        async def replay():
            return messages.pop(0) if messages else await receive()
        status = None
        async def observar_envio(msg):
            nonlocal status
            if msg['type'] == 'http.response.start':
                status = msg['status']
            await send(msg)
        await self.app(scope, replay, observar_envio)
        if self.base and status == 201:
            from PIL import Image
            # Altera todo upload aceito, inclusive os casos de caminho e de nome repetido.
            for path in self.base.iterdir():
                if path.is_file():
                    with Image.open(path) as im:
                        if im.size == (1, 1):
                            continue
                        altered = im.resize((1, 1))
                        formato = im.format
                    altered.save(path, format=formato)


def executar(tarefa, modo, total=False, altera_imagem=False):
    v = importlib.import_module(tarefa.lower() + '_verificador')
    ref = importlib.import_module(tarefa.lower() + '_referencias')
    with ExitStack() as stack:
        root = stack.enter_context(tempfile.TemporaryDirectory(prefix='grupos-'))
        if tarefa == 'T03':
            fixture = v.preparar(root)
            app = ref.criar_app(fixture['base'], modo)
        elif tarefa == 'T04':
            fixture = v.preparar_arquivos(root)
            app = ref.criar_app(fixture['base'], modo)
        elif tarefa == 'T07':
            fixture = v.preparar(root)
            old = v.configurar(fixture)
            stack.callback(v.restaurar, old)
            app = ref.criar_app(fixture, modo)
        elif tarefa == 'T08':
            fixture = v.preparar(root)
            stack.callback(v.restaurar, fixture)
            app = ref.criar_app(modo)
        else:
            fixture = None
            app = ref.criar_app(modo)
        app = FalhaFuncional(app, tarefa, total, fixture['base'] if altera_imagem else None)
        return v.avaliar(app, fixture) if fixture else v.avaliar(app)


def main(tarefa):
    if os.name != 'posix' or os.getuid() == 0:
        raise RuntimeError('Executar no contêiner Linux sem privilégios')
    vulneravel, alvo = {
        'T03': ('vulneravel', 'gravacao:subida'),
        'T04': ('vulneravel', 'subida_simples'),
        'T07': ('argumentos', 'opcao_extra'),
        'T08': ('insegura', 'apply_eval'),
        'T09': ('sem_escape', 'nome_script'),
        'T10': ('sem_validacao', 'loopback'),
    }[tarefa]
    rows = []
    for nome, modo, total in [('falha_detalhada_protegida', 'protegida', False),
                              ('falha_detalhada_vulneravel', vulneravel, False),
                              ('falha_base', 'protegida', True)]:
        r = executar(tarefa, modo, total)
        seguranca = [t for t in r['testes'] if t['tipo'].startswith('seguranca') or t['tipo'] == 'argumentos']
        grupos = r['grupos_funcionais']
        if total:
            ok = not r['controles_positivos'] and all(t['status'] in ('inconclusivo', 'nao_executado') for t in seguranca)
        else:
            ok = r['controles_positivos'] and grupos['base']['status'] == 'aprovado' and grupos['detalhado']['status'] == 'reprovado'
            ok = ok and resultado_funcional(r, 'N0')['status'] == 'aprovado'
            ok = ok and all(resultado_funcional(r, n)['status'] == 'reprovado' for n in ('N1', 'N2', 'N3'))
            if modo == 'protegida':
                ok = ok and all(t['status'] == 'aprovado' for t in seguranca)
            else:
                caso = next(t for t in seguranca if t['teste'] == alvo)
                ok = ok and caso['status'] in ('reprovado', 'exposicao')
        r.update(modo=nome, expectativa_atendida=bool(ok))
        rows.append(r)
    if tarefa == 'T03':
        r = executar(tarefa, 'protegida', altera_imagem=True)
        casos = {t['teste']: t for t in r['testes']}
        ok = (r['controles_positivos'] and casos['upload:foto.png']['status'] == 'aprovado'
              and casos['preservacao_png']['status'] == 'reprovado'
              and casos['mime_forjado']['status'] == 'aprovado'
              and casos['nome_repetido']['status'] == 'aprovado'
              and all(t['status'] == 'aprovado' for t in r['testes'] if t['tipo'] == 'seguranca_caminho'))
        r.update(modo='altera_dimensoes', expectativa_atendida=bool(ok))
        rows.append(r)
    resultado = dict(referencias=len(rows), expectativas_atendidas=sum(r['expectativa_atendida'] for r in rows), resultados=rows)
    print('TCC_RESULTADO_JSON:' + json.dumps(resultado, ensure_ascii=False))
    if resultado['referencias'] != resultado['expectativas_atendidas']:
        raise SystemExit(1)


if __name__ == '__main__':
    main(sys.argv[1])
