import math
from typing import Any
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode, ScalarNode, SequenceNode

app = FastAPI()


class UniqueKeySafeLoader(yaml.SafeLoader):
    pass


def construct_mapping_no_duplicates(loader: UniqueKeySafeLoader, node: MappingNode, deep: bool = False) -> dict:
    if not isinstance(node, MappingNode):
        raise ConstructorError(None, None, "Esperado mapeamento", node.start_mark)
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ConstructorError("Chave duplicada", key_node.start_mark)
        value = loader.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping


UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping_no_duplicates
)


class ConfigPayload(BaseModel):
    yaml: str


def validate_structure_and_depth(node: Any, current_depth: int = 0) -> None:
    if current_depth > 20:
        raise ValueError("Profundidade maxima excedida")

    if isinstance(node, dict):
        for k, v in node.items():
            if not isinstance(k, str):
                raise ValueError("Chave de mapeamento invalida")
            validate_structure_and_depth(v, current_depth + 1)
    elif isinstance(node, list):
        for item in node:
            validate_structure_and_depth(item, current_depth + 1)
    elif isinstance(node, (str, bool)) or node is None:
        pass
    elif isinstance(node, (int, float)):
        if isinstance(node, float) and (math.isnan(node) or math.isinf(node)):
            raise ValueError("Valor numerico nao finito")
    else:
        raise ValueError("Tipo incompativel")


@app.post("/configuracao", status_code=status.HTTP_200_OK)
def importar_configuracao(payload: ConfigPayload) -> dict:
    yaml_text = payload.yaml
    yaml_bytes = yaml_text.encode("utf-8")

    if len(yaml_bytes) > 16384:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Tamanho maximo permitido excedido"
        )

    try:
        loader = UniqueKeySafeLoader(yaml_text)
        try:
            if not loader.check_node():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Documento YAML invalido ou vazio"
                )

            root_node = loader.get_node()

            if loader.check_node():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Multiplos documentos nao permitidos"
                )

            def check_tags(node: Any) -> None:
                standard_tags = {
                    "tag:yaml.org,2002:null",
                    "tag:yaml.org,2002:bool",
                    "tag:yaml.org,2002:int",
                    "tag:yaml.org,2002:float",
                    "tag:yaml.org,2002:str",
                    "tag:yaml.org,2002:seq",
                    "tag:yaml.org,2002:map",
                }
                if node.tag not in standard_tags:
                    raise ValueError("Tag customizada ou nao permitida")
                if isinstance(node, MappingNode):
                    for k, v in node.value:
                        check_tags(k)
                        check_tags(v)
                elif isinstance(node, SequenceNode):
                    for item in node.value:
                        check_tags(item)

            check_tags(root_node)
            parsed_data = loader.construct_document(root_node)
        finally:
            loader.dispose()

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao processar o documento YAML"
        )

    if not isinstance(parsed_data, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A raiz do documento deve ser um mapeamento"
        )

    try:
        validate_structure_and_depth(parsed_data, current_depth=0)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estrutura ou valores invalidos no documento"
        )

    return {"configuracao": parsed_data}