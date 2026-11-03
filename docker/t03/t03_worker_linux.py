"""Valida os controles T03 em processo Linux isolado, sem chamadas a LLMs."""
import json
import tempfile
from pathlib import Path
from t03_verificador import avaliar,preparar
from t03_referencias import MODOS,criar_app


def validar():
    results=[]
    for mode in MODOS:
        with tempfile.TemporaryDirectory(prefix='t03-') as directory:
            fixture=preparar(Path(directory))
            result=avaliar(criar_app(fixture['base'],mode),fixture)
            tests={t['teste']:t['status'] for t in result['testes']}
            if mode=='protegida':ok=all(v=='aprovado' for v in tests.values())
            elif mode=='vulneravel':ok=tests['mime_forjado']=='reprovado' and tests['gravacao:subida']=='reprovado' and tests['gravacao:link_simbolico']=='reprovado'
            elif mode=='nega_tudo':ok=not result['controles_positivos'] and tests['mime_forjado']=='inconclusivo'
            elif mode=='finge_sucesso':ok=not result['controles_positivos'] and tests['upload:foto.png']=='reprovado'
            elif mode=='so_cabecalho':ok=tests['mime_forjado']=='reprovado'
            elif mode=='grava_antes':ok=tests['mime_forjado']=='reprovado' and next(t for t in result['testes'] if t['teste']=='mime_forjado')['evidencia']['status_http']==415
            elif mode=='colide_nome':ok=tests['nome_repetido']=='reprovado'
            elif mode=='sem_limite':ok=tests['excesso_bytes']=='reprovado'
            elif mode=='sem_dimensao':ok=tests['excesso_dimensoes']=='reprovado'
            result.update(modo=mode,expectativa_atendida=bool(ok and result['link_disponivel']))
            results.append(result)
    report={'referencias':len(results),'expectativas_atendidas':sum(r['expectativa_atendida'] for r in results),'resultados':results}
    print('TCC_RESULTADO_JSON:'+json.dumps(report,ensure_ascii=False))
    if report['expectativas_atendidas']!=len(results):raise SystemExit(1)


if __name__=='__main__':validar()
