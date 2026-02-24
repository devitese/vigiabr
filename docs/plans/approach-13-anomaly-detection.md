# Approach: #13 — Standalone Analyzers

## Selected Approach
**Standalone analyzers** — pure functions in `analyzers/` subpackage, new `_analyze()` pipeline phase.

## Pipeline Flow
```
JSONL → _transform(source) → _analyze(result, source) → _validate(result) → _load(result)
                                    │
                                    ├─ reads result.entities['despesas_raw']
                                    ├─ runs benford / hhi / round_values per deputy
                                    └─ appends to result.entities['inconsistencias']
```

## Implementation Order

### 1. Add `scipy` dependency
- **File**: `pipeline/processing/pyproject.toml`
- **Change**: Add `"scipy>=1.12"` to `dependencies` list

### 2. Create `analyzers/constants.py`
- **Source**: `/tmp/CEAP-Playbook/utils/constantes.py:9-23`
- **Adapt**: Replace dict with module-level constants, add `MIN_SAMPLE_SIZE = 50`

### 3. Create `analyzers/benford.py`
- **Source**: `/tmp/CEAP-Playbook/utils/ceap_utils.py:100-201`
- **Adapt**:
  - Input: `list[Decimal]` instead of `pd.Series`
  - Output: `BenfordResult` dataclass (chi2, p_value, significant, n_values, observed, expected)
  - Remove pandas dependency, use stdlib collections
  - Add `MIN_SAMPLE_SIZE` guard (return None if < 50 values)

### 4. Create `analyzers/hhi.py`
- **Source**: `/tmp/CEAP-Playbook/utils/ceap_utils.py:208-298`
- **Adapt**:
  - Input: `list[tuple[str, Decimal]]` (supplier_id, amount) instead of DataFrame
  - Output: `HHIResult` dataclass (hhi, level, n_suppliers, top1_pct, top3_pct, top5_pct)
  - Remove pandas dependency

### 5. Create `analyzers/round_values.py`
- **Source**: `/tmp/CEAP-Playbook/utils/ceap_utils.py:305-350`
- **Adapt**:
  - Input: `list[Decimal]` instead of `pd.Series`
  - Output: `RoundValuesResult` dataclass (pct_round, total_values, round_count)
  - Keep tolerance-based float comparison

### 6. Create `analyzers/__init__.py`
- **Exports**: `analyze_expenses(despesas_raw: list[dict]) -> list[InconsistenciaPendingSchema]`
- This is the orchestrator: groups expenses by deputy, runs all 3 analyzers per deputy, converts results to Inconsistencia pending schemas

### 7. Add `InconsistenciaPendingSchema` to `base.py`
- **File**: `pipeline/processing/processing/transformers/base.py`
- **Add**: Schema with `mandatario_id_externo: str` instead of `mandatario_id: UUID`
- Follows existing pattern (see `MandatarioVotoCreateSchema`)

### 8. Modify `CamaraTransformer` to process expenses
- **File**: `pipeline/processing/processing/transformers/camara.py`
- **Changes**:
  - Remove `"despesa"` from `_SKIPPED_TYPES` (line 29)
  - Add `_transform_despesa(record, result)` — validates via `CamaraDespesaRaw`, appends to `result.entities['despesas_raw']` as raw dicts (not domain entities)
  - Import `CamaraDespesaRaw` from raw models

### 9. Add `_analyze()` phase to `__main__.py`
- **File**: `pipeline/processing/processing/__main__.py`
- **Add** function `_analyze(result: TransformResult, source: str) -> TransformResult`
  - Only runs for `source == "camara"` (for now)
  - Calls `analyze_expenses(result.entities.pop('despesas_raw', []))`
  - Appends returned inconsistencias to `result.entities['inconsistencias']`
- Insert call between `_transform()` and `_validate()` in `main()`

### 10. Update existing test
- **File**: `pipeline/processing/tests/test_transformers.py:152-168`
- **Change**: `TestCamaraSkippedAndInvalid.test_skipped_types` — update to test that despesa records ARE now processed (buffered into `despesas_raw`)

### 11. Write analyzer unit tests
- **File**: `pipeline/processing/tests/test_analyzers.py`
- **Tests**:
  - `test_benford_uniform` — uniform distribution should be significant
  - `test_benford_conforming` — Benford-distributed data should not be significant
  - `test_benford_small_sample` — returns None for < 50 values
  - `test_hhi_monopoly` — single supplier → HHI = 10000
  - `test_hhi_competitive` — many equal suppliers → low HHI
  - `test_hhi_concentrated` — 2 suppliers → correct HHI
  - `test_round_all_round` — all multiples of 1000 → 100%
  - `test_round_none_round` — no round values → 0%
  - `test_round_mixed` — mix → correct percentage
  - `test_analyze_expenses_integration` — full pipeline with mock data, verify Inconsistencia output

## Testing Strategy
- All analyzer functions are pure (no I/O) → easy to unit test
- Use deterministic data (no randomness in tests)
- Integration test in `test_analyzers.py` verifies `analyze_expenses()` end-to-end with fabricated expense dicts

## Inconsistencia Types Generated

| Analyzer | `tipo` | `descricao_neutra` template | `metrica` |
|---|---|---|---|
| Benford | `benford_desvio` | "Distribuicao dos primeiros digitos das despesas desvia da Lei de Benford (chi2={chi2:.1f}, p={p:.4f})" | `"chi2={chi2:.1f};p={p:.4f};n={n}"` |
| HHI | `hhi_concentracao` | "Concentracao de fornecedores acima do limiar (HHI={hhi:.0f}, nivel={nivel})" | `"hhi={hhi:.0f};top1={top1:.1f}%;n_fornecedores={n}"` |
| Round values | `valores_redondos` | "Percentual de valores redondos acima do limiar ({pct:.1f}% de {total} transacoes)" | `"pct_redondos={pct:.1f};n={total}"` |

## score_impacto Calculation
- Each analyzer maps its result to a 0-250 score proportional to severity
- Benford: lower p-value → higher score (e.g., p < 0.001 → 250, p < 0.01 → 150, p < 0.05 → 50)
- HHI: higher HHI → higher score (e.g., MUITO_ALTO → 250, ALTO → 150, MODERADO → 50)
- Round values: higher percentage → higher score (e.g., > 60% → 250, > 45% → 150, > 30% → 50)
