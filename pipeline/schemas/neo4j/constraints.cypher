// VigiaBR — Neo4j Uniqueness Constraints
// Run this script once against a fresh Neo4j database.

// Entity node uniqueness
CREATE CONSTRAINT mandatario_id_tse IF NOT EXISTS FOR (m:Mandatario) REQUIRE m.id_tse IS UNIQUE;
CREATE CONSTRAINT partido_sigla IF NOT EXISTS FOR (p:Partido) REQUIRE p.sigla IS UNIQUE;
CREATE CONSTRAINT pessoa_cpf_hash IF NOT EXISTS FOR (pf:PessoaFisica) REQUIRE pf.cpf_hash IS UNIQUE;
CREATE CONSTRAINT empresa_cnpj IF NOT EXISTS FOR (e:Empresa) REQUIRE e.cnpj IS UNIQUE;
CREATE CONSTRAINT emenda_numero IF NOT EXISTS FOR (em:Emenda) REQUIRE em.numero IS UNIQUE;
CREATE CONSTRAINT contrato_numero IF NOT EXISTS FOR (c:ContratoGov) REQUIRE c.numero IS UNIQUE;
CREATE CONSTRAINT votacao_id_externo IF NOT EXISTS FOR (v:Votacao) REQUIRE v.id_externo IS UNIQUE;
CREATE CONSTRAINT processo_numero_cnj IF NOT EXISTS FOR (pj:ProcessoJudicial) REQUIRE pj.numero_cnj IS UNIQUE;
CREATE CONSTRAINT inconsistencia_id IF NOT EXISTS FOR (i:Inconsistencia) REQUIRE i.id IS UNIQUE;

// Composite key constraints
CREATE CONSTRAINT projeto_lei_key IF NOT EXISTS FOR (pl:ProjetoLei) REQUIRE (pl.tipo, pl.numero, pl.ano) IS UNIQUE;
CREATE CONSTRAINT bem_patrimonial_key IF NOT EXISTS FOR (b:BemPatrimonial) REQUIRE (b.mandatario_id_tse, b.tipo, b.ano_eleicao, b.valor_declarado) IS UNIQUE;
