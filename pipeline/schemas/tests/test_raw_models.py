"""Tests for raw JSONL Pydantic models."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal


from models.raw.camara_raw import (
    CamaraDeputadoRaw,
    CamaraVotacaoRaw,
    CamaraVotoRaw,
    CamaraDespesaRaw,
    CamaraProposicaoRaw,
)
from models.raw.senado_raw import SenadoSenadorRaw, SenadoVotacaoRaw
from models.raw.tse_raw import TseCandidatoRaw, TseBemDeclaradoRaw, TseDoacaoRaw
from models.raw.transparencia_raw import TransparenciaEmendaRaw, TransparenciaContratoRaw
from models.raw.cnpj_raw import CnpjEmpresaRaw, CnpjSocioRaw
from models.raw.querido_diario_raw import QueridoDiarioNomeacaoRaw
from models.raw.cnj_raw import CnjProcessoRaw, CnjParteRaw


class TestCamaraRaw:
    def test_deputado(self):
        dep = CamaraDeputadoRaw(
            id=12345,
            nome="João da Silva",
            sigla_partido="PT",
            sigla_uf="SP",
        )
        assert dep.type == "deputado"
        assert dep.id == 12345

    def test_votacao_with_votos(self):
        votacao = CamaraVotacaoRaw(
            id_votacao="VOT-001",
            data=datetime(2024, 3, 15, 14, 30, tzinfo=timezone.utc),
            descricao="PL 1234/2024",
            votos=[
                CamaraVotoRaw(id_deputado=1, voto="Sim"),
                CamaraVotoRaw(id_deputado=2, voto="Não"),
            ],
        )
        assert len(votacao.votos) == 2
        assert votacao.votos[0].voto == "Sim"

    def test_despesa(self):
        d = CamaraDespesaRaw(
            id_deputado=1,
            ano=2024,
            mes=6,
            tipo_despesa="PASSAGENS AÉREAS",
            valor_liquido=Decimal("1500.00"),
        )
        assert d.type == "despesa"

    def test_proposicao(self):
        p = CamaraProposicaoRaw(id=999, tipo="PL", numero=1234, ano=2024)
        assert p.type == "proposicao"


class TestSenadoRaw:
    def test_senador(self):
        s = SenadoSenadorRaw(
            codigo=5678, nome="Maria Oliveira", sigla_partido="MDB", sigla_uf="RJ"
        )
        assert s.type == "senador"

    def test_votacao(self):
        v = SenadoVotacaoRaw(
            codigo_sessao="SES-001",
            data=datetime(2024, 5, 10, 10, 0, tzinfo=timezone.utc),
            descricao="PLC 45/2024",
        )
        assert v.type == "votacao"


class TestTseRaw:
    def test_candidato(self):
        c = TseCandidatoRaw(
            sequencial="001",
            nome="José Santos",
            cpf="12345678901",
            cargo="DEPUTADO FEDERAL",
            sigla_uf="MG",
            ano_eleicao=2022,
        )
        assert c.type == "candidato"

    def test_bem_declarado(self):
        b = TseBemDeclaradoRaw(
            sequencial_candidato="001",
            ano_eleicao=2022,
            tipo_bem="Apartamento",
            valor=Decimal("450000.00"),
        )
        assert b.valor == Decimal("450000.00")

    def test_doacao(self):
        d = TseDoacaoRaw(
            sequencial_candidato="001",
            ano_eleicao=2022,
            valor=Decimal("50000.00"),
            nome_doador="Empresa XYZ LTDA",
            tipo_doador="PJ",
        )
        assert d.tipo_doador == "PJ"


class TestTransparenciaRaw:
    def test_emenda(self):
        e = TransparenciaEmendaRaw(
            numero="EM-001",
            autor="Dep. Teste",
            ano=2024,
            valor_pago=Decimal("1000000.00"),
        )
        assert e.type == "emenda"

    def test_contrato(self):
        c = TransparenciaContratoRaw(
            numero="CT-001",
            orgao="Ministerio da Saude",
            valor=Decimal("5000000.00"),
            data_assinatura=date(2024, 1, 15),
        )
        assert c.type == "contrato"


class TestCnpjRaw:
    def test_empresa(self):
        e = CnpjEmpresaRaw(
            cnpj_basico="12345678",
            razao_social="EMPRESA TESTE LTDA",
            natureza_juridica="2062",
            capital_social=Decimal("100000.00"),
            porte="EPP",
        )
        assert e.type == "empresa"

    def test_socio(self):
        s = CnpjSocioRaw(
            cnpj_basico="12345678",
            tipo_socio=2,
            nome_socio="Socio Teste",
        )
        assert s.tipo_socio == 2


class TestQueridoDiarioRaw:
    def test_nomeacao(self):
        n = QueridoDiarioNomeacaoRaw(
            nome="Funcionario Nomeado",
            cargo="DAS-4",
            tipo="DAS",
            data_publicacao=date(2024, 6, 1),
        )
        assert n.type == "nomeacao"


class TestCnjRaw:
    def test_processo(self):
        p = CnjProcessoRaw(
            numero_cnj="1234567-89.2024.8.26.0001",
            classe="Ação Civil Pública",
            tribunal="TJSP",
            partes=[
                CnjParteRaw(nome="Ministério Público", tipo="Autor"),
                CnjParteRaw(nome="Réu Teste", tipo="Reu"),
            ],
        )
        assert len(p.partes) == 2
        assert p.type == "processo"
