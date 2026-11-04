"""Grupos funcionais dos instrumentos v3; não modifica resultados históricos."""

DETALHADOS = {
    'T03': {'upload:foto.jpg', 'upload:foto com acento ç.PNG', 'preservacao_png'},
    'T04': {'download:relatorio com acento ç.txt'},
    'T07': {'relatorio:3', 'relatorio:4', 'relatorio:5'},
    'T08': {'unicode_bloco', 'aliases'},
    'T09': {'acentos', 'aspas', 'e_comercial', 'perfis_separados'},
    'T10': {'consulta'},
}


def grupo(tarefa, caso):
    return 'detalhado' if caso['teste'] in DETALHADOS[tarefa] else 'base'


def base_aprovada(tarefa, testes):
    base = [t for t in testes if t['tipo'] == 'funcional' and grupo(tarefa, t) == 'base']
    return bool(base) and all(t['status'] == 'aprovado' for t in base)


def registrar_grupos(tarefa, testes):
    for t in testes:
        if t['tipo'] == 'funcional':
            t['grupo_funcional'] = grupo(tarefa, t)
            t['exigido_desde'] = 'N1' if t['grupo_funcional'] == 'detalhado' else 'N0'
    resumo = {}
    for nome in ('base', 'detalhado'):
        casos = [t for t in testes if t.get('grupo_funcional') == nome]
        resumo[nome] = dict(casos=len(casos), aprovados=sum(t['status'] == 'aprovado' for t in casos),
                            status='nao_avaliado' if not casos else 'aprovado' if all(t['status'] == 'aprovado' for t in casos) else 'reprovado')
    return resumo


def resultado_funcional(resultado, nivel):
    """Aplica os requisitos do nível, preservando o diagnóstico dos demais casos."""
    if nivel not in ('N0', 'N1', 'N2', 'N3'):
        raise ValueError(nivel)
    exigidos = ('base',) if nivel == 'N0' else ('base', 'detalhado')
    grupos = resultado.get('grupos_funcionais', {})
    estados = [grupos.get(g, {}).get('status', 'nao_avaliado') for g in exigidos]
    status = ('inconclusivo' if 'nao_avaliado' in estados else
              'aprovado' if all(s == 'aprovado' for s in estados) else 'reprovado')
    return dict(nivel=nivel, grupos_exigidos=list(exigidos), status=status)
