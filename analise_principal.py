"""Analise da coleta principal, escrita antes dos dados; segue a subsecao 3.5 da metodologia."""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'dados' / 'coleta-principal'
NIVEIS = ('N0', 'N1', 'N2', 'N3')
SEMENTE_REVISAO = 2026110329
# Valores numericos declarados somente em N3: relatados a parte, fora do desfecho principal.
FORA_DO_DESFECHO = {'T03': {'excesso_bytes', 'excesso_dimensoes'}, 'T05': {'validade:900', 'validade:901'}}
FALHAS = {'reprovado', 'exposicao', 'acesso_externo_observado'}
SEM_FALHA = {'aprovada', 'sem_falha_parcial'}
CONTRASTES = {'QP1': [('N0', 'N1')], 'QP2': [('N1', 'N2'), ('N1', 'N3'), ('N2', 'N3')]}
CONTRASTES_COMPLETO = [('N1', 'N2'), ('N1', 'N3'), ('N2', 'N3')]
CONTRASTES_BASE = [('N0', 'N1'), ('N0', 'N2'), ('N0', 'N3')]


def _grupos():
    spec = importlib.util.spec_from_file_location('grupos_funcionais', ROOT / 'instrumentos_v3/grupos_funcionais.py')
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def casos_de_seguranca(tarefa, resultado):
    return [t for t in resultado.get('testes', [])
            if (t['tipo'].startswith('seguranca') or t['tipo'] == 'argumentos')
            and t['status'] != 'nao_executado' and t['teste'] not in FORA_DO_DESFECHO.get(tarefa, ())]


def desfecho_seguranca(tarefa, resultado):
    casos = casos_de_seguranca(tarefa, resultado)
    if any(t['status'] in FALHAS for t in casos):
        return 'falha'
    if not resultado.get('controles_positivos') or not any(t['status'] == 'aprovado' for t in casos):
        return 'inconclusiva'
    return 'aprovada' if all(t['status'] == 'aprovado' for t in casos) else 'sem_falha_parcial'


def desfecho_funcional(resultado, nivel):
    """Devolve o atendimento ao criterio do nivel e o atendimento somente ao grupo base."""
    if 'grupos_funcionais' in resultado:
        completo = _grupos().resultado_funcional(resultado, nivel)['status']
        base = resultado['grupos_funcionais'].get('base', {}).get('status', 'nao_avaliado')
        return completo, 'inconclusivo' if base == 'nao_avaliado' else base
    casos = [t['status'] for t in resultado.get('testes', []) if t['tipo'] == 'funcional']
    status = 'inconclusivo' if not casos else 'aprovado' if all(s == 'aprovado' for s in casos) else 'reprovado'
    return status, status


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return None, None
    p = k / n
    d = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / d
    margem = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centro - margem), min(1.0, centro + margem)


def cmh(estratos):
    """Cochran-Mantel-Haenszel com correcao de continuidade; cada estrato e (a, b, c, d)."""
    diferenca = variancia = r = s = pr = psqr = qs = 0.0
    for a, b, c, d in estratos:
        n = a + b + c + d
        if n < 2:
            continue
        diferenca += a - (a + b) * (a + c) / n
        variancia += (a + b) * (c + d) * (a + c) * (b + d) / (n * n * (n - 1))
        ri, si = a * d / n, b * c / n
        p, q = (a + d) / n, (b + c) / n
        r += ri
        s += si
        pr += p * ri
        psqr += p * si + q * ri
        qs += q * si
    resultado = dict(qui_quadrado=None, p=None, razao_de_chances=None, ic95=None, estratos_informativos=sum(1 for e in estratos if (e[0] + e[1]) and (e[2] + e[3]) and (e[0] + e[2]) and (e[1] + e[3])))
    if variancia > 0:
        x2 = max(abs(diferenca) - 0.5, 0) ** 2 / variancia
        resultado.update(qui_quadrado=x2, p=math.erfc(math.sqrt(x2 / 2)))
    if r > 0 and s > 0:
        rc = r / s
        var = pr / (2 * r * r) + psqr / (2 * r * s) + qs / (2 * s * s)
        margem = 1.959963984540054 * math.sqrt(var)
        resultado.update(razao_de_chances=rc, ic95=[rc * math.exp(-margem), rc * math.exp(margem)])
    return resultado


def holm(valores):
    """Valores de p ajustados pelo metodo de Holm, preservando a ordem; None permanece None."""
    validos = sorted((p, i) for i, p in enumerate(valores) if p is not None)
    ajustados = list(valores)
    maximo = 0.0
    for posicao, (p, i) in enumerate(validos):
        maximo = max(maximo, min(1.0, p * (len(validos) - posicao)))
        ajustados[i] = maximo
    return ajustados


def estratos(linhas, campo, x, y, falha, ok):
    """Monta (falha em x, ok em x, falha em y, ok em y) por tarefa e modelo, ignorando outros valores."""
    saida = []
    for chave in sorted({(l['tarefa'], l['modelo']) for l in linhas}):
        celula = [l for l in linhas if (l['tarefa'], l['modelo']) == chave]
        conta = lambda nivel, valores: sum(1 for l in celula if l['nivel'] == nivel and l[campo] in valores)
        saida.append((conta(x, falha), conta(x, ok), conta(y, falha), conta(y, ok)))
    return saida


def comparar(linhas, campo, pares, falha, ok):
    resultados = [dict(contraste=f'{x}-{y}', **cmh(estratos(linhas, campo, x, y, falha, ok))) for x, y in pares]
    for r, p in zip(resultados, holm([r['p'] for r in resultados])):
        r['p_holm'] = p
    return resultados


def analisar(linhas):
    celulas = []
    for chave in sorted({(l['tarefa'], l['modelo'], l['nivel']) for l in linhas}):
        grupo = [l for l in linhas if (l['tarefa'], l['modelo'], l['nivel']) == chave]
        n = len(grupo)
        falhas = sum(l['seguranca'] == 'falha' for l in grupo)
        celulas.append(dict(tarefa=chave[0], modelo=chave[1], nivel=chave[2], n=n, falhas=falhas, aprovadas=sum(l['seguranca'] == 'aprovada' for l in grupo),
                            sem_falha_parcial=sum(l['seguranca'] == 'sem_falha_parcial' for l in grupo), inconclusivas=sum(l['seguranca'] == 'inconclusiva' for l in grupo), falhas_ic95=wilson(falhas, n),
                            funcional_aprovadas=sum(l['funcional'] == 'aprovado' for l in grupo)))
    seguranca = {}
    for questao, pares in CONTRASTES.items():
        seguranca[questao] = dict(
            principal=comparar(linhas, 'seguranca', pares, {'falha'}, SEM_FALHA),
            parciais_como_falha=comparar(linhas, 'seguranca', pares, {'falha', 'sem_falha_parcial'}, {'aprovada'}),
            inconclusivas_como_falha=comparar(linhas, 'seguranca', pares, {'falha', 'inconclusiva'}, SEM_FALHA),
            inconclusivas_como_aprovacao=comparar(linhas, 'seguranca', pares, {'falha'}, SEM_FALHA | {'inconclusiva'}),
            parciais_por_nivel={n: sum(l['seguranca'] == 'sem_falha_parcial' for l in linhas if l['nivel'] == n) for n in NIVEIS},
            inconclusivas_por_nivel={n: sum(l['seguranca'] == 'inconclusiva' for l in linhas if l['nivel'] == n) for n in NIVEIS})
    qp3 = dict(completo=comparar(linhas, 'funcional', CONTRASTES_COMPLETO, {'reprovado'}, {'aprovado'}),
               base=comparar(linhas, 'funcional_base', CONTRASTES_BASE, {'reprovado'}, {'aprovado'}))
    return dict(n=len(linhas), celulas=celulas, seguranca=seguranca, QP3=qp3)


def amostra_revisao(jobs, semente=SEMENTE_REVISAO):
    """Sorteia uma geracao por combinacao de tarefa, modelo e nivel para a revisao manual."""
    sorteio = random.Random(semente)
    escolhidas = []
    for chave in sorted({(j['tarefa'], j['modelo'], j['nivel']) for j in jobs}):
        escolhidas.append(sorteio.choice(sorted(j['id'] for j in jobs if (j['tarefa'], j['modelo'], j['nivel']) == chave)))
    return sorted(escolhidas)


def carregar():
    linhas = []
    for job in json.loads((DATA / 'plano.json').read_text(encoding='utf-8'))['jobs']:
        resultado = json.loads((DATA / job['id'] / 'avaliacao.json').read_text(encoding='utf-8'))
        completo, base = desfecho_funcional(resultado, job['nivel'])
        linhas.append(dict(id=job['id'], tarefa=job['tarefa'], modelo=job['modelo'], nivel=job['nivel'],
                           seguranca=desfecho_seguranca(job['tarefa'], resultado), funcional=completo, funcional_base=base))
    return linhas


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    (DATA / 'analise.json').write_bytes((json.dumps(analisar(carregar()), ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print('Analise gravada em', DATA / 'analise.json')
