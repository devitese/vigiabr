"""Transformers — convert raw JSONL records into domain Pydantic schemas."""

from processing.transformers.base import (
    BaseTransformer,
    BemDeclaradoPendingSchema,
    CeisFlagSchema,
    DoacaoCreateSchema,
    MandatarioContratacaoCreateSchema,
    MandatarioVotoCreateSchema,
    TransformError,
    TransformResult,
    VotacaoCreateSchema,
)
from processing.transformers.camara import CamaraTransformer
from processing.transformers.cnj import CnjTransformer
from processing.transformers.cnpj import CnpjTransformer
from processing.transformers.querido_diario import QueridoDiarioTransformer
from processing.transformers.senado import SenadoTransformer
from processing.transformers.transparencia import TransparenciaTransformer
from processing.transformers.tse import TseTransformer

TRANSFORMER_REGISTRY: dict[str, type[BaseTransformer]] = {
    "camara": CamaraTransformer,
    "senado": SenadoTransformer,
    "tse": TseTransformer,
    "transparencia": TransparenciaTransformer,
    "cnpj": CnpjTransformer,
    "querido_diario": QueridoDiarioTransformer,
    "cnj": CnjTransformer,
}

__all__ = [
    # Base
    "BaseTransformer",
    "TransformResult",
    "TransformError",
    # Intermediate schemas
    "VotacaoCreateSchema",
    "MandatarioVotoCreateSchema",
    "DoacaoCreateSchema",
    "BemDeclaradoPendingSchema",
    "CeisFlagSchema",
    "MandatarioContratacaoCreateSchema",
    # Transformers
    "CamaraTransformer",
    "SenadoTransformer",
    "TseTransformer",
    "TransparenciaTransformer",
    "CnpjTransformer",
    "QueridoDiarioTransformer",
    "CnjTransformer",
    # Registry
    "TRANSFORMER_REGISTRY",
]
