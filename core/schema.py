from __future__ import annotations

import re
import unicodedata

CANONICAL_FIELDS = {
    "data": "Data",
    "ocorrencia": "Número da ocorrência",
    "categoria": "Categoria do problema",
    "descricao": "Descrição",
    "fornecedor": "Fornecedor",
    "transportadora": "Transportadora",
    "planta": "Planta",
    "area": "Área",
    "processo": "Processo",
    "produto": "Produto ou peça",
    "embalagem": "Código da embalagem",
    "tipo_embalagem": "Tipo de embalagem",
    "quantidade": "Quantidade",
    "tempo_parada": "Tempo de parada",
    "custo": "Custo",
    "gravidade": "Gravidade",
    "frequencia": "Frequência",
    "responsavel": "Responsável",
    "causa": "Causa",
    "acao": "Ação",
    "prazo": "Prazo",
    "status": "Status",
}

ALIASES = {
    "data": ["data", "date", "dt", "data ocorrencia", "data da ocorrencia"],
    "ocorrencia": ["ocorrencia", "numero ocorrencia", "id", "rdl", "numero rdl"],
    "categoria": ["categoria", "tipo problema", "problema", "defeito", "motivo"],
    "descricao": ["descricao", "detalhe", "observacao", "ocorrido"],
    "fornecedor": ["fornecedor", "supplier", "vendor"],
    "transportadora": ["transportadora", "carrier"],
    "planta": ["planta", "site", "centro"],
    "area": ["area", "setor", "departamento"],
    "processo": ["processo", "etapa", "operacao"],
    "produto": ["produto", "peca", "part number", "material"],
    "embalagem": ["embalagem", "codigo embalagem", "rack", "klt", "glt"],
    "tipo_embalagem": ["tipo embalagem", "familia embalagem"],
    "quantidade": ["quantidade", "qtd", "volume"],
    "tempo_parada": ["tempo parada", "horas paradas", "minutos parada", "duracao"],
    "custo": ["custo", "valor", "impacto financeiro", "debito"],
    "gravidade": ["gravidade", "severidade", "criticidade"],
    "frequencia": ["frequencia", "ocorrencia fmea"],
    "responsavel": ["responsavel", "owner"],
    "causa": ["causa", "causa raiz", "root cause"],
    "acao": ["acao", "acao corretiva", "contramedida"],
    "prazo": ["prazo", "vencimento", "due date"],
    "status": ["status", "situacao"],
}


def normalize(value: object) -> str:
    value = "" if value is None else str(value)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def suggest_mapping(columns: list[object]) -> dict[str, str | None]:
    normalized = {str(col): normalize(col) for col in columns}
    mapping: dict[str, str | None] = {}
    for field, aliases in ALIASES.items():
        alias_set = {normalize(a) for a in aliases}
        exact = next((col for col, norm in normalized.items() if norm in alias_set), None)
        if exact:
            mapping[field] = exact
            continue
        partial = next(
            (col for col, norm in normalized.items() if any(a in norm or norm in a for a in alias_set)),
            None,
        )
        mapping[field] = partial
    return mapping

