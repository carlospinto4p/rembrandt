# Testing Guidelines

## Test Structure

Unit tests live in `tests/unit/` and run with `uv run pytest tests/unit -v`.
They are fast, isolated, and never depend on real data files or
external services. Use fixtures and `tmp_path` for temporary data.

Integration tests live in `tests/integration/` and run separately so
they don't break CI when real data files are absent.

## Style

- **No test classes.** Use plain functions with `test_` prefix.
- Group tests by module, separated by comment headers:
  ```python
  # --- Tag Validation Tests ---
  ```
- Use `pytest` idioms: fixtures, parametrize, `pytest.raises`.
- Keep test files named `test_<module>.py` mirroring the source.

## Fixtures

- Define fixtures in the test file when used by that file only.
- Move shared fixtures to `conftest.py` when used across files.
- Prefer `tmp_path` (built-in) for temporary files/databases.
- Use `@pytest.fixture` without parentheses for consistency.

## Assertions

- One logical assertion per test when possible.
- Use plain `assert` — avoid `unittest`-style methods.
- For float comparisons: `assert abs(actual - expected) < 1e-9`.
- For dict key checks: `assert list(result.keys()) == [...]`.

## Naming

- Test functions: `test_<what>_<scenario>` in snake_case.
  - `test_get_wallet_balance_empty_response`, `test_list_transactions_flattens_nested_data`
- Fixture functions: descriptive nouns (`mock_llm_client`, `sample_exercise`).

## What to Test

- **Do test:** public functions, edge cases, error paths, data
  roundtrips, output schemas of returned models.
- **Don't test:** private helpers directly (test through public
  API), trivial getters/setters.

## Running Tests

```bash
# Unit tests (default, fast)
uv run pytest tests/unit -v
```
