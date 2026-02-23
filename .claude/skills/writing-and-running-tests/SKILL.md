---
name: writing-and-running-tests
description: Write and run tests — auto-detects language and framework
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task
---

# Writing and Running Tests

## Philosophy

Follow TDD when possible. Use `Skill("superpowers:test-driven-development")` for discipline.

## Process

### Step 1: Detect Context

Auto-detect the testing framework:
- **Python files** → pytest (look for `conftest.py`, `tests/` directory)
- **TypeScript/JavaScript** → Jest or Vitest (check `package.json` for test runner)
- **E2E** → Playwright or Cypress (check for config files)

### Step 2: Explore Existing Patterns

Use `Glob` and `Read` to find existing test files and understand patterns:
- Import conventions
- Fixture usage
- Assertion style
- Mock patterns

### Step 3: Write Tests

Follow discovered patterns. For each test:

```python
# Python (pytest)
def test_specific_behavior():
    """Test that <specific thing> produces <expected result>."""
    # Arrange
    input_data = ...

    # Act
    result = function(input_data)

    # Assert
    assert result == expected
```

### Step 4: Run Tests

```bash
# Python
python3 -m pytest tests/ -v

# TypeScript (if applicable)
npx jest --verbose 2>/dev/null || npx vitest run 2>/dev/null || true
```

### Step 5: Fix Failures

If tests fail, auto-fix up to 3 attempts. After 3 failures, stop and report.

### Step 6: Report

- Tests written (count and names)
- Tests passing/failing
- Coverage gaps identified

## Modes

- `--unit` — Unit tests only
- `--e2e` — End-to-end tests only
- `<file-path>` — Tests for a specific file
