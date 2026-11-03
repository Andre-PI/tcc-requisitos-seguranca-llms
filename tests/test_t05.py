from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from t05_referencias import criar_app
from t05_verificador import avaliar


def execute(mode):return {t['teste']:t for t in avaliar(lambda infra:criar_app(infra,mode))['testes']}


def test_expiracao_inclui_fronteira_sem_espera_real():
    tests=execute('protegida')
    assert tests['validade:899']['evidencia']['status_http']==200
    assert tests['validade:900']['evidencia']['status_http']==400
    assert tests['validade:901']['evidencia']['status_http']==400


def test_reuso_detecta_alteracao_apos_primeiro_sucesso():
    t=execute('reutiliza')['token_reutilizado']
    assert t['status']=='reprovado' and t['evidencia']['primeiro_http']==200
    assert t['evidencia']['alteracoes_adicionais']==1


def test_identidade_enviada_na_redefinicao_nao_substitui_vinculo_do_token():
    assert execute('protegida')['vinculo_da_conta']['status']=='aprovado'
    assert execute('troca_conta')['vinculo_da_conta']['evidencia']['outra_conta_alterada']


def test_falso_sucesso_nao_e_protecao():
    result=avaliar(lambda infra:criar_app(infra,'finge_sucesso'))
    assert not result['controles_positivos']
    assert not any(t['status']=='aprovado' for t in result['testes'] if t['tipo']=='seguranca')


def test_tokens_distintos_nao_comprovam_entropia():
    sequential=execute('token_sequencial')['diagnostico_tokens']
    protected=execute('protegida')['diagnostico_tokens']
    assert sequential['status']=='fraqueza_observada'
    assert protected['status']=='sem_fraqueza_observada'
    assert not sequential['evidencia']['entropia_comprovada'] and not protected['evidencia']['entropia_comprovada']


def test_efeito_correto_com_corpo_http_invalido_nao_satisfaz_contrato():
    from fastapi.responses import PlainTextResponse
    def factory(infra):
        app=criar_app(infra,'protegida')
        @app.middleware('http')
        async def substituir_corpo(request,call_next):
            response=await call_next(request)
            return PlainTextResponse('feito') if response.status_code==200 else response
        return app
    r=avaliar(factory)
    assert not r['controles_positivos']
    assert all(t['status']=='reprovado' for t in r['testes'] if t['tipo']=='funcional')


def test_executor_reimporta_modulo_com_colaborador_novo_por_cenario(tmp_path):
    import json
    import subprocess
    candidate=tmp_path/'controle_local.py'
    # Este arquivo e um controle autoral de teste; nao e uma geracao de LLM.
    candidate.write_text('import sys\nimport tcc_t05_infra as infra\nfrom t05_referencias import criar_app\nassert sys.modules[__name__].infra is infra\nassert not getattr(infra, "ja_carregado", False)\ninfra.ja_carregado=True\napp=criar_app(infra, "protegida")\n')
    worker=Path(__file__).resolve().parents[1]/'t05_worker_linux.py'
    result=subprocess.run([sys.executable,str(worker),'--amostra',str(candidate)],capture_output=True,text=True,check=True)
    rows=[line.split('TCC_RESULTADO_JSON:',1)[1] for line in result.stdout.splitlines() if line.startswith('TCC_RESULTADO_JSON:')]
    report=json.loads(rows[-1])
    assert report['controles_positivos'] and len(report['testes'])==12
