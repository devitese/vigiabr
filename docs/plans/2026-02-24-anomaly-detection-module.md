# Anomaly Detection Module Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring Benford's Law, HHI concentration, and round values detection from CEAP-Playbook into VigiaBR's processing pipeline as a new `analyzers` subpackage that produces `Inconsistencia` records.

**Architecture:** Pure-function analyzers run as a standalone pipeline phase (`_analyze()`) between `_transform()` and `_validate()`. The CamaraTransformer buffers validated expense records; the analyze phase groups them by deputy, runs 3 statistical tests per deputy, and emits `InconsistenciaPendingSchema` records into the `TransformResult`. The loader resolves external IDs to UUIDs at write time.

**Tech Stack:** Python 3.12+, scipy (chi-squared test), numpy (logarithms), Pydantic (schemas)

---

## Context

VigiaBR has a complete data pipeline (7 Scrapy spiders, Airflow DAGs, PostgreSQL + Neo4j loaders) but **zero anomaly detection code**. The `Inconsistencia` model exists in the DB schema but nothing generates records for it. Meanwhile, the [CEAP-Playbook](https://github.com/jpvss/CEAP-Playbook) repository has battle-tested statistical functions for detecting expense anomalies, validated against a real case (Operacao Galho Fraco).

The CamaraTransformer currently **skips** expense records (`_SKIPPED_TYPES = {"despesa", "frente"}`). The raw Pydantic model `CamaraDespesaRaw` already exists with all needed fields.

## Selected Approach

**Standalone analyzers** — pure functions in a new `processing/analyzers/` subpackage with a new `_analyze()` pipeline phase.

Rationale:
- Analyzers are pure functions (easy to test, no I/O)
- Single-responsibility: transformers transform, analyzers analyze
- New pipeline phase is explicit and auditable in logs
- No changes to loader or validator logic

## Alternatives Considered

1. **Analyzer inside transformer** — run analyses at the end of `CamaraTransformer.transform()`. Rejected: breaks single-responsibility, makes transformer too complex.
2. **Separate CLI command** — `python -m processing analyze camara` reads from PG. Rejected: requires a new `despesas_ceap` table and a second pipeline step; over-engineered for MVP.

---

## Implementation Tasks

### Task 1: Add scipy dependency
**Files:** `pipeline/processing/pyproject.toml`
**Steps:**
1. Add `"scipy>=1.12"` to the `dependencies` list
2. Run `uv sync` in the processing workspace to verify resolution

**Tests:** `uv pip check` passes

---

### Task 2: Create analyzer constants
**Files:** `pipeline/processing/processing/analyzers/__init__.py`, `pipeline/processing/processing/analyzers/constants.py`
**Steps:**
1. Create `analyzers/` directory with `__init__.py`
2. Create `constants.py` with thresholds adapted from CEAP-Playbook `constantes.py:9-23`:
   ```python
   # HHI thresholds (CADE standard)
   HHI_LOW = 1500
   HHI_MODERATE = 2500
   HHI_HIGH = 5000

   # Benford's Law
   BENFORD_P_VALUE = 0.05

   # Round values
   ROUND_VALUES_THRESHOLD = 0.30  # 30%
   ROUND_DIVISORS = [1000, 500]
   ROUND_TOLERANCE = 0.01

   # Minimum sample size for statistical tests
   MIN_SAMPLE_SIZE = 50
   ```

**Tests:** Import succeeds

---

### Task 3: Create Benford analyzer
**Files:** `pipeline/processing/processing/analyzers/benford.py`
**Source:** CEAP-Playbook `ceap_utils.py:100-201`
**Steps:**
1. Define `BenfordResult` dataclass: `chi2`, `p_value`, `significant`, `n_values`, `observed: dict[int, float]`, `expected: dict[int, float]`
2. Implement `benford_expected() -> dict[int, float]` — Benford distribution for digits 1-9
3. Implement `extract_first_digit(value: Decimal) -> int | None` — first significant digit
4. Implement `benford_analysis(values: list[Decimal]) -> BenfordResult | None`:
   - Return `None` if len(valid values) < `MIN_SAMPLE_SIZE`
   - Use `collections.Counter` instead of pandas
   - Use `scipy.stats.chisquare()` for the test
   - Return `BenfordResult` with significance flag

**Key adaptations from CEAP-Playbook:**
- `pd.Series` → `list[Decimal]`
- `valores.apply()` → list comprehension
- `value_counts()` → `collections.Counter`

**Tests:**
- `test_benford_uniform` — digits uniformly distributed → significant deviation
- `test_benford_conforming` — data following Benford distribution → not significant
- `test_benford_small_sample` — < 50 values → returns None
- `test_benford_empty` — empty list → returns None

---

### Task 4: Create HHI analyzer
**Files:** `pipeline/processing/processing/analyzers/hhi.py`
**Source:** CEAP-Playbook `ceap_utils.py:208-298`
**Steps:**
1. Define `HHIResult` dataclass: `hhi`, `level` (str), `n_suppliers`, `top1_pct`, `top3_pct`, `top5_pct`
2. Implement `calculate_hhi(shares: list[float]) -> float` — sum of squared shares * 10000
3. Implement `interpret_hhi(hhi: float) -> str` — LOW/MODERATE/HIGH/VERY_HIGH
4. Implement `hhi_analysis(expenses: list[tuple[str, Decimal]]) -> HHIResult | None`:
   - Input: list of (supplier_id, amount) tuples
   - Group by supplier, compute shares
   - Return `None` if only 1 supplier (trivial monopoly) or no data
   - Return `HHIResult`

**Key adaptations from CEAP-Playbook:**
- `pd.DataFrame.groupby()` → `collections.defaultdict` aggregation
- `pd.Series` division → manual share calculation

**Tests:**
- `test_hhi_monopoly` — single supplier → HHI = 10000
- `test_hhi_competitive` — 10 equal suppliers → HHI = 1000 (LOW)
- `test_hhi_concentrated` — 80/20 split → HHI = 6800 (VERY_HIGH)
- `test_hhi_empty` — no expenses → returns None

---

### Task 5: Create round values analyzer
**Files:** `pipeline/processing/processing/analyzers/round_values.py`
**Source:** CEAP-Playbook `ceap_utils.py:305-350`
**Steps:**
1. Define `RoundValuesResult` dataclass: `pct_round`, `total_values`, `round_count`
2. Implement `is_round_value(value: Decimal, divisors, tolerance) -> bool`
3. Implement `round_values_analysis(values: list[Decimal]) -> RoundValuesResult | None`:
   - Return `None` if empty list
   - Count values divisible by 1000 or 500 (with float tolerance)
   - Return percentage and counts

**Tests:**
- `test_round_all_round` — all multiples of 1000 → 100%
- `test_round_none_round` — e.g., [123.45, 678.90] → 0%
- `test_round_mixed` — known mix → correct percentage
- `test_round_empty` — empty list → returns None

---

### Task 6: Create analyzer orchestrator
**Files:** `pipeline/processing/processing/analyzers/__init__.py`
**Steps:**
1. Define `InconsistenciaPendingSchema` in `transformers/base.py`:
   ```python
   class InconsistenciaPendingSchema(BaseSchema):
       mandatario_id_externo: str
       tipo: str
       descricao_neutra: str
       metrica: Optional[str] = None
       score_impacto: int = Field(ge=0, le=250)
       fontes: list[str] = []
   ```
2. Implement `analyze_expenses(despesas_raw: list[dict]) -> list[InconsistenciaPendingSchema]`:
   - Group expense dicts by `id_deputado`
   - For each deputy with enough data:
     - Run `benford_analysis()` on their `valor_liquido` values
     - Run `hhi_analysis()` on their (supplier, amount) pairs
     - Run `round_values_analysis()` on their `valor_liquido` values
   - Convert flagged results to `InconsistenciaPendingSchema` with:
     - `mandatario_id_externo = str(id_deputado)`
     - `tipo` / `descricao_neutra` / `metrica` per analyzer
     - `score_impacto` mapped from severity
     - `fontes = ["dadosabertos.camara.leg.br"]`
3. Implement `_benford_score(p_value)`, `_hhi_score(hhi)`, `_round_score(pct)` — map to 0-250

**score_impacto mapping:**
| Analyzer | Condition | Score |
|---|---|---|
| Benford | p < 0.001 | 200 |
| Benford | p < 0.01 | 120 |
| Benford | p < 0.05 | 50 |
| HHI | VERY_HIGH (>5000) | 200 |
| HHI | HIGH (>2500) | 120 |
| HHI | MODERATE (>1500) | 50 |
| Round | > 60% | 200 |
| Round | > 45% | 120 |
| Round | > 30% | 50 |

**Tests:**
- `test_analyze_expenses_integration` — fabricate expense dicts for 2 deputies, one with anomalous data, verify correct InconsistenciaPendingSchema output

---

### Task 7: Wire CamaraTransformer to process expenses
**Files:** `pipeline/processing/processing/transformers/camara.py`
**Steps:**
1. Remove `"despesa"` from `_SKIPPED_TYPES` (line 29)
2. Add `"despesa"` to `_HANDLED_TYPES` (line 27)
3. Add import: `from models.raw.camara_raw import CamaraDespesaRaw`
4. Add method:
   ```python
   def _transform_despesa(self, record: dict, result: TransformResult) -> None:
       raw = CamaraDespesaRaw.model_validate(record)
       result.add_entity("despesas_raw", raw.model_dump())
   ```
5. Add dispatch in `transform()`:
   ```python
   elif record_type == "despesa":
       self._transform_despesa(record, result)
   ```

**Tests:** Update `test_skipped_types` in `test_transformers.py` to verify despesas are now buffered into `despesas_raw`

---

### Task 8: Add `_analyze()` phase to pipeline CLI
**Files:** `pipeline/processing/processing/__main__.py`
**Steps:**
1. Add import: `from processing.analyzers import analyze_expenses`
2. Add function:
   ```python
   def _analyze(result: TransformResult, source: str) -> TransformResult:
       if source == "camara":
           despesas_raw = result.entities.pop("despesas_raw", [])
           if despesas_raw:
               inconsistencias = analyze_expenses(despesas_raw)
               for inc in inconsistencias:
                   result.add_entity("inconsistencias", inc)
               logger.info("Analysis complete — %d inconsistencias detected", len(inconsistencias))
       return result
   ```
3. Insert call in `main()` between `_transform()` and `_validate()`:
   ```python
   result = _transform(args.source, args.data_dir)
   result = _analyze(result, args.source)  # NEW
   result = _validate(result)
   ```
4. Add `"despesas_raw"` handling: since `despesas_raw` is popped before validate/load, it won't flow to PG or Neo4j (no table needed)

**Tests:** Covered by integration test in Task 6

---

### Task 9: Update existing tests
**Files:** `pipeline/processing/tests/test_transformers.py`
**Steps:**
1. Update `TestCamaraSkippedAndInvalid.test_skipped_types`:
   - Change assertion: despesa records now produce entities in `despesas_raw`
   - `assert result.total_entities == 1`
   - `assert "despesas_raw" in result.entities`
2. Add new test `test_despesa_transform`:
   - Full despesa record with all fields → validates via `CamaraDespesaRaw`, appears in `despesas_raw`

---

### Task 10: Write analyzer unit tests
**Files:** `pipeline/processing/tests/test_analyzers.py`
**Steps:**
1. Write all tests listed in Tasks 3-6 above
2. Integration test `test_analyze_expenses_integration`:
   - Create ~100 expense dicts for deputy A (normal distribution)
   - Create ~100 expense dicts for deputy B (all values are round multiples of 1000, single supplier)
   - Run `analyze_expenses()`
   - Verify deputy A has 0 or fewer inconsistencias
   - Verify deputy B has inconsistencias for HHI and round values

---

## Test Plan

| Layer | What | How |
|---|---|---|
| Unit | Each analyzer function | Deterministic inputs, assert exact outputs |
| Unit | Transformer despesa buffering | Mock records, check `despesas_raw` in result |
| Integration | `analyze_expenses()` orchestrator | Fabricated data, verify InconsistenciaPendingSchema output |
| Smoke | `python -m processing camara --dry-run` | With sample JSONL, verify no crashes and summary includes inconsistencias count |

Run all: `cd pipeline/processing && uv run pytest tests/ -v`

---

## Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| scipy adds ~30MB to Docker image | Low | Acceptable tradeoff; no lighter chi-squared implementation |
| Benford unreliable with small samples | Medium | `MIN_SAMPLE_SIZE = 50` guard; return None if insufficient data |
| Thresholds may need tuning | Medium | Constants are in one file (`constants.py`), easy to adjust after running against full dataset |
| mandatario_id resolution at load time | Low | Follow existing `MandatarioVotoCreateSchema` pattern; loader already resolves external IDs |
| despesas_raw could be large in memory | Low | Expense records are small dicts; ~200k records for full mandato fits in <500MB |

---

## File Summary

| Action | File | Description |
|---|---|---|
| Create | `pipeline/processing/processing/analyzers/__init__.py` | Orchestrator + exports |
| Create | `pipeline/processing/processing/analyzers/constants.py` | Thresholds |
| Create | `pipeline/processing/processing/analyzers/benford.py` | Benford's Law |
| Create | `pipeline/processing/processing/analyzers/hhi.py` | HHI concentration |
| Create | `pipeline/processing/processing/analyzers/round_values.py` | Round values |
| Create | `pipeline/processing/tests/test_analyzers.py` | All analyzer tests |
| Modify | `pipeline/processing/pyproject.toml` | Add scipy dependency |
| Modify | `pipeline/processing/processing/transformers/base.py` | Add InconsistenciaPendingSchema |
| Modify | `pipeline/processing/processing/transformers/camara.py` | Process expenses |
| Modify | `pipeline/processing/processing/__main__.py` | Add _analyze() phase |
| Modify | `pipeline/processing/tests/test_transformers.py` | Update skipped-types test |
