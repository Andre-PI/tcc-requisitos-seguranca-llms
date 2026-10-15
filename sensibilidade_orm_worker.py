"""Condicao EXPLORATORIA g103: completa o contrato ORM; nao e resultado principal."""
import json
import sys
from pathlib import Path
import comportamento_worker as w


def main():
    source,output=sys.argv[1:]
    adaptations=[]
    module,app=w.load(source,'T06',adaptations)
    external=sys.modules['models']
    assert not hasattr(module.Pedido,'__table__')
    module.Pedido=external.Pedido
    module.ItemPedido=external.ItemPedido
    adaptations.append('CONDICAO EXTRA: classes placeholder Pedido/ItemPedido substituidas em memoria por modelos ORM do contrato. Nenhuma condicao SQL ou de autorizacao alterada. Nao equivale a execucao direta da amostra.')
    tests=w.t06(module,app,Path(source).read_text(encoding='utf-8'),adaptations)
    result=dict(condicao='complementacao_orm_fora_da_analise_principal',adaptacoes=adaptations,testes=tests)
    Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main()
