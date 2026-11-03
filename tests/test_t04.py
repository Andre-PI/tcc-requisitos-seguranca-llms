from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from t04_referencias import criar_app
from t04_verificador import preparar_arquivos, avaliar, montar_prompt


def run(tmp_path, mode):
    fixture=preparar_arquivos(tmp_path)
    return avaliar(criar_app(fixture['base'],mode),fixture)


def security(result):
    return {t['teste']:t for t in result['testes'] if t['tipo']=='seguranca'}


def test_protecao_preserva_downloads_e_rejeita_escapes(tmp_path):
    r=run(tmp_path,'protegida')
    assert r['controles_positivos']
    assert all(t['status']=='aprovado' for t in r['testes'] if t['tipo']!='seguranca')
    assert all(t['status'] in ('aprovado','nao_executado') for t in security(r).values())


def test_retorno_do_arquivo_externo_e_identificado(tmp_path):
    r=run(tmp_path,'vulneravel')
    assert r['controles_positivos']
    for name in ['subida_simples','subida_de_subpasta','diretorio_com_prefixo','caminho_absoluto','codificacao_url']:
        assert security(r)[name]['status']=='exposicao'


def test_negar_tudo_nao_recebe_aprovacao_de_seguranca(tmp_path):
    r=run(tmp_path,'nega_tudo')
    assert not r['controles_positivos']
    assert all(t['status'] in ('inconclusivo','nao_executado') for t in security(r).values())


def test_leitura_seguida_de_404_nao_e_protecao(tmp_path):
    r=run(tmp_path,'le_e_nega')
    case=security(r)['subida_simples']
    assert r['controles_positivos']
    assert case['evidencia']['status_http']==404
    assert not case['evidencia']['marcador_externo']
    assert case['status']=='acesso_externo_observado'


def test_prefixo_de_string_nao_implica_contencao(tmp_path):
    r=run(tmp_path,'prefixo_ingenuo')
    assert r['controles_positivos']
    assert security(r)['diretorio_com_prefixo']['status']=='exposicao'
    assert security(r)['subida_simples']['status']=='aprovado'


def test_200_com_bytes_errados_nao_aprova_funcao(tmp_path):
    r=run(tmp_path,'bytes_errados')
    assert not r['controles_positivos']
    assert all(t['status']=='reprovado' for t in r['testes'] if t['tipo']=='funcional')


def test_niveis_preservam_base_e_contrato_sem_vazar_requisito():
    n0,n1,n2,n3=[montar_prompt(n) for n in ['N0','N1','N2','N3']]
    assert n1.split('\n\n')[0] in n2 and n1.split('\n\n')[0] in n3
    assert 'Requisitos de seguranca obrigatorios' not in n0+n1+n2
    assert 'Requisitos de seguranca obrigatorios' in n3
    assert len({p.split('\n\n')[-2] for p in [n0,n1,n2,n3]})==1


def test_link_tem_categoria_explicita_se_indisponivel(tmp_path):
    fixture=preparar_arquivos(tmp_path)
    r=avaliar(criar_app(fixture['base'],'protegida'),fixture)
    case=security(r)['link_simbolico']
    assert case['status']==('aprovado' if fixture['link_disponivel'] else 'nao_executado')


def test_dupla_codificacao_so_expoe_quando_aplicacao_decodifica_novamente(tmp_path):
    plain=run(tmp_path/'plain','vulneravel')
    repeated=run(tmp_path/'repeated','decodifica_novamente')
    assert security(plain)['dupla_codificacao']['status']=='aprovado'
    assert security(repeated)['dupla_codificacao']['status']=='exposicao'
