# Graph Relationship Model Design

**Date:** 2026-02-24
**Status:** Approved
**Scope:** Neo4j graph schema, relationship types, proximity model, confidence levels, aggregation strategy, pair comparison

---

## 1. Problem Statement

VigiaBR needs a well-defined graph model that answers two primary questions for every politician:
1. **"Who benefits from this politician?"** — Follow money outward (contracts, amendments, hiring)
2. **"Who influences this politician?"** — Follow influence inward (donations, party ties, business connections)

The model must support:
- Up to 3 degrees of proximity (direct + 2 intermediaries)
- Pair comparison between two politicians (shortest path)
- Confidence levels on every relationship (data provenance)
- Aggregation of high-cardinality entities (votes, amendments) for visualization

---

## 2. Node Catalog (11 types)

| Node | Identity Key | Role |
|------|-------------|------|
| `Mandatario` | `id_tse` | Politician — always the center of the graph |
| `PessoaFisica` | `cpf_hash` | Any natural person (family, aide, donor, partner) |
| `Empresa` | `cnpj` | Company |
| `Partido` | `sigla` | Political party |
| `BemPatrimonial` | composite (`mandatario_id_tse`, `tipo`, `ano_eleicao`, `valor_declarado`) | Declared asset |
| `Emenda` | `numero` | Parliamentary amendment |
| `ContratoGov` | `numero` | Government contract |
| `Votacao` | `id_externo` | Roll-call vote session |
| `ProjetoLei` | composite (`tipo`, `numero`, `ano`) | Bill/legislation |
| `ProcessoJudicial` | `numero_cnj` | Public lawsuit |
| `Inconsistencia` | `id` | Detected inconsistency (output node, not traversable) |

---

## 3. Edge Catalog (14 relationship types)

### Degree 1 — Direct connections (politician's inner circle)

| Edge | From | To | Properties | Data Source |
|------|------|----|-----------|-------------|
| `FILIADO_A` | Mandatario | Partido | data_filiacao, data_desfiliacao | TSE |
| `TEM_FAMILIAR` | Mandatario | PessoaFisica | grau (conjuge/filho/irmao/etc) | TSE + CNPJ cross-ref |
| `CONTRATOU_GABINETE` | Mandatario | PessoaFisica | cargo, salario, data_inicio | Portal Transparencia |
| `TEM_BEM` | Mandatario | BemPatrimonial | *(implicit via FK)* | TSE patrimonio |
| `VOTOU` | Mandatario | Votacao | voto (Sim/Nao/Abstencao/Ausente/Obstrucao), data | Camara/Senado API |
| `AUTOU_EMENDA` | Mandatario | Emenda | *(FK)* | Portal Transparencia |
| `DOOU` | PessoaFisica or Empresa | Mandatario | valor, eleicao_ano, data | TSE donations |

**User sees:** "Deputy X is in Party Y, has family member Maria, hired aide Joao, declared R$2M in assets, authored 15 amendments, received donations from Company Z."

### Degree 2 — Connections of the inner circle

| Edge | From | To | Properties | Data Source |
|------|------|----|-----------|-------------|
| `SOCIO_DE` | PessoaFisica | Empresa | percentual_cotas, data_entrada, data_saida | Receita Federal CNPJ |
| `BENEFICIOU` | Emenda | Empresa | valor_pago, fonte_url | CGU payment records |
| `FINANCIOU` | Emenda | ContratoGov | valor | Portal Transparencia |
| `EXECUTOU` | ContratoGov | Empresa | *(FK)* | Portal Transparencia |
| `PARTE_EM` | PessoaFisica | ProcessoJudicial | polo (autor/reu), data | CNJ DataJud |
| `REFERE_A` | Votacao | ProjetoLei | *(links vote to bill)* | Camara/Senado API |
| `AUTOU_PL` | Mandatario | ProjetoLei | tipo_autoria (autor/relator/coautor) | Camara/Senado API |

**User sees:** "Deputy X's brother is 40% partner in Company ABC. Amendment #1234 funded contract #5678 awarded to Company ABC."

### Degree 3 — Extended web (same edge types, further hops)

Degree 3 uses the SAME relationship types but traverses one more hop from degree 2 entities:
- Other partners of the same company (`SOCIO_DE`)
- Other contracts with same company (`EXECUTOU`)
- Lawsuits involving 2nd-degree entities (`PARTE_EM`)
- Same company/person donating to OTHER politicians (`DOOU`)
- Other politicians in same party (`FILIADO_A`)

**User sees:** "Company ABC (where Deputy X's brother is partner) also has partner Carlos, who donated to Senator Y."

---

## 4. Confidence Model

Every edge carries a `confianca` property:

| Level | Label | Meaning | Visual Style | Used in SCI? |
|-------|-------|---------|-------------|-------------|
| `A` | Confirmado | Direct match from authoritative source | Solid line | Yes |
| `B` | Cruzado | Cross-referenced between 2+ official sources | Solid line, lighter | Yes |
| `C` | Inferido | Single-source heuristic match (e.g., surname match) | Dashed line | No |
| `D` | Reportado | External source (journalism, crowdsource) | Dotted line | No |

### Confidence per relationship type

| Edge | Confidence A | Confidence B | Confidence C |
|------|-------------|-------------|-------------|
| `FILIADO_A` | TSE party registration | — | — |
| `TEM_FAMILIAR` | TSE spouse declaration | CNPJ co-partner + shared address | Surname match only |
| `CONTRATOU_GABINETE` | Portal Transparencia staff list | Querido Diario appointment | — |
| `SOCIO_DE` | Receita Federal CNPJ dump | — | — |
| `DOOU` | TSE campaign donations | — | — |
| `AUTOU_EMENDA` | Portal Transparencia / Camara API | — | — |
| `VOTOU` | Camara / Senado API | — | — |
| `BENEFICIOU` | CGU payment records | Contract chain | — |
| `EXECUTOU` | Portal Transparencia contracts | — | — |
| `PARTE_EM` | CNJ DataJud | — | — |

### UI rules

1. Default view shows only `A` and `B` confidence relationships
2. User can toggle `C` and `D` visibility (opt-in)
3. `C` and `D` relationships display "requer verificacao" label
4. SCI score calculation only uses `A` and `B` relationships
5. Every edge carries `fonte_url` — direct link to the official data source

---

## 5. Aggregation Strategy for Visualization

High-cardinality entities (votes, amendments, assets, staff) are shown as **cluster nodes** to prevent visualization spam.

| Entity | Expected Count | Strategy | Cluster Label |
|--------|---------------|----------|---------------|
| `Partido` | 1-3 | Individual nodes | — |
| `PessoaFisica` (family) | 2-15 | Individual nodes | — |
| `PessoaFisica` (staff) | 5-50 | Cluster if >10 | "25 assessores, R$380K/mes" |
| `BemPatrimonial` | 5-100 | Cluster if >10 | "47 bens, R$5.2M total" |
| `Votacao` | 500-3,000+ | Always cluster | "2,847 votos" |
| `Emenda` | 10-200+ | Cluster if >10 | "87 emendas, R$120M" |
| `Empresa` (via SOCIO_DE) | 1-20 | Individual nodes | — |
| `ContratoGov` | 1-50 | Cluster if >10 | "32 contratos, R$45M" |
| `ProcessoJudicial` | 0-10 | Individual nodes | — |
| `ProjetoLei` | 10-500+ | Cluster if >10 | "143 projetos" |
| Resolved donors | 5-100+ | Cluster if >10 | "42 doadores, R$2.3M" |

### Rules

1. **Threshold = 10**: Entities with count > 10 are shown as a single cluster node
2. **Always individual**: `PessoaFisica(family)`, `Empresa(via SOCIO_DE)`, `ProcessoJudicial` — too important to aggregate
3. **Cluster label**: Shows count + total monetary value (when applicable)
4. **Click to expand**: User clicks cluster to see individual nodes with sorting/filtering
5. **Cluster nodes** use dashed-border rounded rectangles to visually distinguish from individual nodes

---

## 6. Pair Comparison (Shortest Path)

### How it works

1. User selects two politicians
2. System runs Neo4j shortest path query:
   ```cypher
   MATCH path = shortestPath(
     (a:Mandatario {id_tse: $id1})-[*..6]-(b:Mandatario {id_tse: $id2})
   )
   WHERE ALL(r IN relationships(path) WHERE r.confianca IN ['A', 'B'])
   RETURN path
   ORDER BY length(path)
   LIMIT 5
   ```
3. Results show top 5 shortest paths with:
   - Full chain of entities
   - Confidence level per hop
   - Monetary value per hop (when applicable)
   - Total proximity score

### Constraints

- Max 6 hops (3 degrees from each politician)
- Default: only traverses A+B confidence edges
- User can opt-in to include C+D edges (with warning)
- Shows top 5 shortest paths ranked by proximity score

### Proximity Score Formula

```
proximity_score = sum(hop_weights) / max_possible_weight

hop_weight = type_weight * confidence_weight * value_factor

type_weight:
  TEM_FAMILIAR = 1.0 (strongest)
  SOCIO_DE = 0.9
  CONTRATOU_GABINETE = 0.8
  DOOU = 0.7
  EXECUTOU = 0.6
  BENEFICIOU = 0.6
  FILIADO_A = 0.5
  PARTE_EM = 0.4
  VOTOU = 0.2
  REFERE_A = 0.1

confidence_weight:
  A = 1.0
  B = 0.8
  C = 0.5
  D = 0.3

value_factor:
  log10(monetary_value + 1) / 10  (normalized, 0-1 range)
  1.0 if no monetary value applies
```

---

## 7. Neo4j Schema Changes Required

### New relationship types to add

```cypher
// Already in schema (keep):
// FILIADO_A, TEM_FAMILIAR, CONTRATOU (rename to CONTRATOU_GABINETE), SOCIO_DE, RECEBEU_DOACAO (rename to DOOU), VOTOU

// New edges:
// AUTOU_EMENDA — Mandatario -> Emenda
// TEM_BEM — Mandatario -> BemPatrimonial
// DOOU — PessoaFisica/Empresa -> Mandatario (replaces Doacao table for graph)
// BENEFICIOU — Emenda -> Empresa
// FINANCIOU — Emenda -> ContratoGov
// EXECUTOU — ContratoGov -> Empresa
// PARTE_EM — PessoaFisica -> ProcessoJudicial
// REFERE_A — Votacao -> ProjetoLei
// AUTOU_PL — Mandatario -> ProjetoLei
```

### New properties on all edges

```cypher
// Every relationship gets:
// - confianca: 'A' | 'B' | 'C' | 'D'
// - fonte_url: String (direct link to source data)
// - data_coleta: Date (when the data was collected)
```

### New indexes

```cypher
CREATE INDEX rel_confianca IF NOT EXISTS FOR ()-[r:SOCIO_DE]-() ON (r.confianca);
CREATE INDEX rel_confianca_doou IF NOT EXISTS FOR ()-[r:DOOU]-() ON (r.confianca);
CREATE INDEX rel_confianca_beneficiou IF NOT EXISTS FOR ()-[r:BENEFICIOU]-() ON (r.confianca);
CREATE INDEX rel_confianca_executou IF NOT EXISTS FOR ()-[r:EXECUTOU]-() ON (r.confianca);
CREATE INDEX rel_confianca_parte_em IF NOT EXISTS FOR ()-[r:PARTE_EM]-() ON (r.confianca);
```

---

## 8. PostgreSQL Schema Changes Required

### New junction tables

- `emenda_beneficiarios` — Emenda -> Empresa (BENEFICIOU)
- `emenda_contratos` — Emenda -> ContratoGov (FINANCIOU)
- `mandatario_projetos_lei` — Mandatario -> ProjetoLei (AUTOU_PL)
- `pessoa_processos` — PessoaFisica -> ProcessoJudicial (PARTE_EM)

### Modified tables

- `mandatario_contratacoes` — rename concept to CONTRATOU_GABINETE (table name can stay)
- `doacoes` — add `doador_entity_id` FK (optional, for resolved donors graph edge)
- All junction tables — add `confianca` (VARCHAR(1)), `fonte_url` (TEXT), `data_coleta` (DATE)

---

## 9. Prototype

Interactive HTML prototype at: `docs/prototypes/graph-viz-prototype.html`

Features demonstrated:
- 3-degree concentric ring layout
- Cluster nodes for high-cardinality entities
- Click-to-expand clusters
- Click-to-highlight path back to center
- Degree filtering controls
- Tooltip with entity details

---

## 10. Data Source Limitations

| Relationship | Data Quality | Notes |
|-------------|-------------|-------|
| `FILIADO_A` | High (A) | TSE registration is authoritative |
| `TEM_FAMILIAR` | Low-Medium (B-C) | No single authoritative source for family trees. TSE has spouse only. CNPJ cross-ref for others. |
| `CONTRATOU_GABINETE` | High (A) | Portal Transparencia staff lists are public |
| `SOCIO_DE` | High (A) | Receita Federal CNPJ dumps are authoritative |
| `DOOU` | High (A) | TSE campaign donation records are authoritative |
| `BENEFICIOU` | Medium (A-B) | CGU payment records exist but linking amendment-to-payment requires chain |
| `EXECUTOU` | High (A) | Portal Transparencia contracts are authoritative |
| `PARTE_EM` | High (A) | CNJ DataJud is authoritative |
| `VOTOU` | High (A) | Camara/Senado APIs are authoritative |

---

## 11. Implementation Priority

1. **Schema changes** — Add new edges, confidence fields, indexes
2. **Neo4j loader** — Update to support new relationship types and confidence
3. **Transformers** — Update each source transformer to emit confidence levels
4. **Graph query service** — Degree-based traversal API, pair comparison
5. **Aggregation logic** — Cluster computation for high-cardinality entities
6. **Frontend integration** — Cytoscape.js with degree controls and cluster expand
