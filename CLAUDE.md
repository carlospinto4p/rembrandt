# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core Rules

1. **Self-Improvement**: When the user corrects a mistake, ALWAYS update the relevant guidelines (`.claude/rules/` or this file) to prevent it from happening again.

2. **Keep CLAUDE.md Minimal**: Do not include library schemas, architecture details, or information discoverable from the codebase. Keep only essential rules and commands here.

3. **Update CLAUDE.md Each Iteration**: Review and update this file when rules change or new important patterns emerge.

## Project Overview

Rembrandt is a Python library for mental exercises with the help of LLMs.

## Common Commands

**IMPORTANT**: Always use `uv run` to execute Python commands. Never run raw `python` commands.

```bash
# Install dependencies
uv sync --all-extras

# Run unit tests
uv run pytest tests/unit -v

# Run linter
uv run ruff check src/ tests/

# Run linter with auto-fix
uv run ruff check src/ tests/ --fix
```

## Code Style

- Line length: 78 characters (enforced by ruff)
- Pydantic v2 for data validation
- Type hints required
- Docstring style: Sphinx/reST (`:param:`, `:return:`, `:raises:`)
- In docstrings, use single backticks (`` `name` ``) not double (`` ``name`` ``)
