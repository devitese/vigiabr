# Exploration: #13 — Anomaly Detection Module (Benford, HHI, Round Values)

## Context Summary
- Issue: #13 — feat(analysis): add anomaly detection module (Benford, HHI, round values)
- Area: `pipeline/processing` — new `analyzers` subpackage
- Complexity: **medium**
- Source: [CEAP-Playbook](https://github.com/jpvss/CEAP-Playbook) `/tmp/CEAP-Playbook/utils/`

## Core Files (will change)

### New files to create
- `pipeline/processing/processing/analyzers/__init__.py` — public API
- `pipeline/processing/processing/analyzers/benford.py` — Benford's Law analysis (adapted from `ceap_utils.py:100-201`)
- `pipeline/processing/processing/analyzers/hhi.py` — HHI concentration index (adapted from `ceap_utils.py:208-298`)
- `pipeline/processing/processing/analyzers/round_values.py` — round value detection (adapted from `ceap_utils.py:305-350`)
- `pipeline/processing/processing/analyzers/constants.py` — thresholds (adapted from `constantes.py:9-23`)
- `pipeline/processing/tests/test_analyzers.py` — unit tests

### Existing files to modify
- `pipeline/processing/processing/transformers/camara.py:29` — remove `"despesa"` from `_SKIPPED_TYPES`, add `_transform_despesa()` method
- `pipeline/processing/processing/__main__.py` — add analysis phase between validate and load (or after transform)
- `pipeline/processing/pyproject.toml` — add `scipy` dependency (needed for chi-squared test)

## Supporting Files (context, won't change)

- `pipeline/schemas/models/inconsistencia.py` — `InconsistenciaCreateSchema` target output: `tipo`, `descricao_neutra`, `metrica`, `score_impacto` (0-250), `fontes`, `mandatario_id`
- `pipeline/schemas/models/raw/camara_raw.py:50-62` — `CamaraDespesaRaw` already defined with all needed fields: `id_deputado`, `valor_liquido`, `cnpj_cpf_fornecedor`, `nome_fornecedor`, `tipo_despesa`
- `pipeline/processing/processing/transformers/base.py` — `TransformResult` (entities + relationships + errors), `BaseTransformer` ABC
- `pipeline/processing/processing/validators/data_quality.py` — existing validator pattern (dedup + range + length checks)
- `/tmp/CEAP-Playbook/utils/ceap_utils.py` — source functions to adapt
- `/tmp/CEAP-Playbook/utils/constantes.py` — source thresholds

## Key Architecture Observations

### Pipeline flow (current)
```
raw JSONL → Transformer.transform() → TransformResult → DataQualityValidator → Loaders (PG + Neo4j)
```

### Analysis placement decision
The analyzers operate on **aggregated** data (per-deputy, per-category), not individual records. This means they cannot run inside `transform()` which processes records one-by-one. They must run as a **post-transform** phase that takes the full `TransformResult` and produces additional `Inconsistencia` entities.

### CamaraDespesaRaw already exists
The raw Pydantic model at `camara_raw.py:50-62` is already defined and exported. The transformer just needs to parse it and store the expense records for analysis.

### Inconsistencia uses mandatario_id (UUID)
The `InconsistenciaCreateSchema` references `mandatario_id` as `Optional[uuid.UUID]`. But during transform, we only have `id_tse` (external ID). We need a pending schema like `InconsistenciaPendingSchema` with `mandatario_id_externo` that the loader resolves to a UUID — same pattern used by `MandatarioVotoCreateSchema`.

### No expense domain schema exists
Unlike votacoes/proposicoes, there is **no domain entity for expenses** (no `DespesaCreateSchema`). The analyzers consume raw expense records directly — they don't need a separate PG table for individual expenses. The output is `Inconsistencia` records, not expense records.

## Dependencies

| Dependency | Status | Notes |
|---|---|---|
| `scipy` | **New** — needs adding to `pyproject.toml` | For `scipy.stats.chisquare()` in Benford analysis |
| `numpy` | Already available via `scipy` | For `np.log10()` in Benford expected distribution |
| `pandas` | **Not used** in pipeline | CEAP-Playbook uses pandas `Series`; we'll adapt to work with plain `list[Decimal]` |
| `pydantic` | Already available | For `InconsistenciaCreateSchema` |

## Test Coverage

### Existing tests
- `pipeline/processing/tests/test_transformers.py` — Tests CamaraTransformer for deputado, votacao, proposicao. Has test that despesa is SKIPPED (line 152-168) — **this test will need updating**.
- `pipeline/processing/tests/test_validators.py` — Tests DataQualityValidator

### Gaps
- No analyzer tests exist (module doesn't exist yet)
- No test for expense transformation
- No integration test for transform → analyze → Inconsistencia pipeline

## Risks

1. **scipy adds ~30MB to the Docker image** — acceptable tradeoff for chi-squared test; no lighter alternative that doesn't reimplement the math
2. **Analyzer needs aggregated data, transform is record-by-record** — solve by collecting expense records in a buffer during transform, then running analyzers in a post-pass
3. **mandatario_id resolution** — analyzers produce results keyed by `id_deputado` (external), need a pending schema or loader resolution step (existing pattern in codebase)
4. **Threshold tuning** — CEAP-Playbook thresholds are validated against one case study (Op. Galho Fraco); may need adjustment after running against full dataset
5. **Benford minimum sample size** — chi-squared test is unreliable with small samples; need a minimum transaction count (e.g., 50+) per deputy before flagging
