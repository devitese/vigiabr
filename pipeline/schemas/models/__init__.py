"""VigiaBR schemas — SQLAlchemy ORM models and Pydantic validation schemas."""

from models.base import Base, TimestampMixin
from models.mandatario import Mandatario, MandatarioSchema
from models.partido import Partido, PartidoSchema
from models.pessoa_fisica import PessoaFisica, PessoaFisicaSchema
from models.empresa import Empresa, EmpresaSchema
from models.bem_patrimonial import BemPatrimonial, BemPatrimonialSchema
from models.emenda import Emenda, EmendaSchema
from models.contrato_gov import ContratoGov, ContratoGovSchema
from models.votacao import Votacao, VotacaoSchema, MandatarioVoto, MandatarioVotoSchema
from models.projeto_lei import ProjetoLei, ProjetoLeiSchema
from models.processo_judicial import ProcessoJudicial, ProcessoJudicialSchema
from models.inconsistencia import Inconsistencia, InconsistenciaSchema

__all__ = [
    "Base",
    "TimestampMixin",
    "Mandatario",
    "MandatarioSchema",
    "Partido",
    "PartidoSchema",
    "PessoaFisica",
    "PessoaFisicaSchema",
    "Empresa",
    "EmpresaSchema",
    "BemPatrimonial",
    "BemPatrimonialSchema",
    "Emenda",
    "EmendaSchema",
    "ContratoGov",
    "ContratoGovSchema",
    "Votacao",
    "VotacaoSchema",
    "MandatarioVoto",
    "MandatarioVotoSchema",
    "ProjetoLei",
    "ProjetoLeiSchema",
    "ProcessoJudicial",
    "ProcessoJudicialSchema",
    "Inconsistencia",
    "InconsistenciaSchema",
]
