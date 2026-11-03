"""Utilitario ficticio T07. As opcoes adversas existem somente para os controles."""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import sys


def render(data,categoria,formato):
    items=[{k:r[k] for k in ('produto','quantidade','preco_centavos')} for r in data if r['categoria']==categoria]
    if formato=='json':
        return json.dumps(dict(categoria=categoria,itens=items,quantidade=sum(r['quantidade'] for r in items),total_centavos=sum(r['quantidade']*r['preco_centavos'] for r in items)),ensure_ascii=False)
    out=io.StringIO();writer=csv.DictWriter(out,fieldnames=['produto','quantidade','preco_centavos']);writer.writeheader();writer.writerows(items)
    return out.getvalue()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--formato',choices=['json','csv'],required=True)
    parser.add_argument('--emitir-marcador');parser.add_argument('categoria',nargs='?',default='')
    args=parser.parse_args()
    with Path(os.environ['TCC_RELATORIO_LOG']).open('a',encoding='utf-8') as out:
        out.write(json.dumps(dict(categoria=args.categoria,formato=args.formato,argv=sys.argv[1:]))+'\n')
    if args.emitir_marcador:Path(args.emitir_marcador).write_text('T07_OPCAO_FICTICIA',encoding='utf-8')
    if args.categoria=='falha_controlada':
        print('T07_ERRO_INTERNO_FICTICIO /runner/dados_internos',file=sys.stderr);return 17
    data=json.loads(Path(os.environ['TCC_RELATORIO_DADOS']).read_text(encoding='utf-8'))
    print(render(data,args.categoria,args.formato));return 0


if __name__=='__main__':raise SystemExit(main())
