import math
import yaml
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI()

MAX_YAML_BYTES = 16384
MAX_DEPTH = 20

ALLOWED_TAG_PREFIXES = ("tag:yaml.org,2002:",)
ALLOWED_TAGS = {
    "tag:yaml.org,2002:null",
    "tag:yaml.org,2002:bool",
    "tag:yaml.org,2002:int",
    "tag:yaml.org,2002:float",
    "tag:yaml.org,2002:str",
    "tag:yaml.org,2002:seq",
    "tag:yaml.org,2002:map",
}


class StrictSafeLoader(yaml.SafeLoader):
    pass


def construct_mapping(loader, node, deep=False):
    if not isinstance(node, yaml.MappingNode):
        raise yaml.constructor.ConstructorError(
            None, None, "esperado nó de mapeamento", node.start_mark
        )
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise yaml.constructor.ConstructorError(
                "construção de chave",
                node.start_mark,
                "chave de mapeamento deve ser string",
                key_node.start_mark,
            )
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "construção de chave",
                node.start_mark,
                "chave duplicada encontrada",
                key_node.start_mark,
            )
        value = loader.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping


StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
)


def validate_node(node, depth=0, visited_nodes=None):
    if visited_nodes is None:
        visited_nodes = set()

    if id(node) in visited_nodes:
        raise ValueError("Referência cíclica detectada.")
    visited_nodes.add(id(node))

    if node.tag and (
        node.tag not in ALLOWED_TAGS
        or not any(node.tag.startswith(prefix) for prefix in ALLOWED_TAG_PREFIXES)
    ):
        raise ValueError("Tag YAML inválida ou não permitida.")

    if depth > MAX_DEPTH:
        raise ValueError("Profundidade máxima de aninhamento excedida.")

    if isinstance(node, yaml.MappingNode):
        seen_keys = set()
        for key_node, value_node in node.value:
            if not isinstance(key_node, yaml.ScalarNode) or key_node.tag not in (
                "tag:yaml.org,2002:str",
                yaml.resolver.BaseResolver.DEFAULT_SCALAR_TAG,
            ):
                raise ValueError("Chaves do mapeamento devem ser strings.")
            if key_node.value in seen_keys:
                raise ValueError("Chave duplicada detectada.")
            seen_keys.add(key_node.value)

            validate_node(key_node, depth, set(visited_nodes))
            validate_node(value_node, depth + 1, set(visited_nodes))

    elif isinstance(node, yaml.SequenceNode):
        for item_node in node.value:
            validate_node(item_node, depth + 1, set(visited_nodes))

    elif isinstance(node, yaml.ScalarNode):
        pass
    else:
        raise ValueError("Tipo de nó não suportado.")


def validate_json_types(obj, depth=0, visited_ids=None):
    if visited_ids is None:
        visited_ids = set()

    if id(obj) in visited_ids:
        raise ValueError("Estrutura cíclica detectada.")
    visited_ids.add(id(obj))

    if depth > MAX_DEPTH:
        raise ValueError("Profundidade máxima excedida.")

    if obj is None or isinstance(obj, (bool, str)):
        return
    elif isinstance(obj, (int, float)):
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            raise ValueError("Valores numéricos infinitos ou NaN não são suportados.")
        return
    elif isinstance(obj, list):
        for item in obj:
            validate_json_types(item, depth + 1, set(visited_ids))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise ValueError("Chaves de mapeamento devem ser strings.")
            validate_json_types(v, depth + 1, set(visited_ids))
    else:
        raise ValueError("Tipo de valor incompatível com JSON.")


class ConfigRequest(BaseModel):
    yaml: str


@app.post("/configuracao")
def importar_configuracao(req: ConfigRequest):
    yaml_bytes = req.yaml.encode("utf-8")
    if len(yaml_bytes) > MAX_YAML_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Tamanho do YAML excede o limite permitido.",
        )

    try:
        loader = StrictSafeLoader(req.yaml)
        try:
            if not loader.check_node():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Documento YAML vazio ou inválido.",
                )
            root_node = loader.get_node()
            if loader.check_node():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Múltiplos documentos YAML não são suportados.",
                )
        finally:
            loader.dispose()

        if not isinstance(root_node, yaml.MappingNode):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A raiz da configuração deve ser um mapeamento.",
            )

        validate_node(root_node, depth=0)

        data = yaml.load(req.yaml, Loader=StrictSafeLoader)

        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A raiz da configuração deve ser um mapeamento.",
            )

        validate_json_types(data, depth=0)

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao processar documento YAML. Entrada inválida.",
        )

    return {"configuracao": data}