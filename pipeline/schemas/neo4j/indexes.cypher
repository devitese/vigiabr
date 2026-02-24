// VigiaBR — Neo4j Indexes for query performance
// Run after constraints.cypher (constraints already create indexes on constrained properties).

// Lookup indexes for common query patterns
CREATE INDEX mandatario_nome IF NOT EXISTS FOR (m:Mandatario) ON (m.nome);
CREATE INDEX mandatario_uf IF NOT EXISTS FOR (m:Mandatario) ON (m.uf);
CREATE INDEX mandatario_cargo IF NOT EXISTS FOR (m:Mandatario) ON (m.cargo);
CREATE INDEX mandatario_sci IF NOT EXISTS FOR (m:Mandatario) ON (m.sci_score);

CREATE INDEX empresa_cnae IF NOT EXISTS FOR (e:Empresa) ON (e.cnae);
CREATE INDEX empresa_situacao IF NOT EXISTS FOR (e:Empresa) ON (e.situacao);

CREATE INDEX emenda_ano IF NOT EXISTS FOR (em:Emenda) ON (em.ano);
CREATE INDEX emenda_tipo IF NOT EXISTS FOR (em:Emenda) ON (em.tipo);

CREATE INDEX votacao_data IF NOT EXISTS FOR (v:Votacao) ON (v.data);

CREATE INDEX contrato_orgao IF NOT EXISTS FOR (c:ContratoGov) ON (c.orgao_contratante);
CREATE INDEX contrato_data IF NOT EXISTS FOR (c:ContratoGov) ON (c.data_assinatura);

CREATE INDEX processo_tribunal IF NOT EXISTS FOR (pj:ProcessoJudicial) ON (pj.tribunal);
CREATE INDEX processo_tipo IF NOT EXISTS FOR (pj:ProcessoJudicial) ON (pj.tipo);

CREATE INDEX inconsistencia_tipo IF NOT EXISTS FOR (i:Inconsistencia) ON (i.tipo);
CREATE INDEX inconsistencia_data IF NOT EXISTS FOR (i:Inconsistencia) ON (i.data_deteccao);
CREATE INDEX inconsistencia_impacto IF NOT EXISTS FOR (i:Inconsistencia) ON (i.score_impacto);

// Relationship property indexes for temporal queries
CREATE INDEX rel_votou_data IF NOT EXISTS FOR ()-[r:VOTOU]-() ON (r.data);
CREATE INDEX rel_doacao_valor IF NOT EXISTS FOR ()-[r:RECEBEU_DOACAO]-() ON (r.valor);
CREATE INDEX rel_doacao_ano IF NOT EXISTS FOR ()-[r:RECEBEU_DOACAO]-() ON (r.eleicao_ano);
CREATE INDEX rel_filiacao_data IF NOT EXISTS FOR ()-[r:FILIADO_A]-() ON (r.data_filiacao);
CREATE INDEX rel_socio_entrada IF NOT EXISTS FOR ()-[r:SOCIO_DE]-() ON (r.data_entrada);
