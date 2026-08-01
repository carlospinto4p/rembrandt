# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core Rules

1. **Self-Improvement**: When the user corrects a mistake, ALWAYS update the relevant guidelines (`.claude/rules/` or this file) to prevent it from happening again.

2. **Keep CLAUDE.md Minimal**: Do not include library schemas, architecture details, or information discoverable from the codebase. Keep only essential rules and commands here.

3. **Update CLAUDE.md Each Iteration**: Review and update this file when rules change or new important patterns emerge.

4. **Periodic Reviews**: Triggered by backlog depth — when `/backlog` shows fewer than 5 open items, propose `/scan`, `/improvements`, and `/prune` together.

## Project Overview

Rembrandt is a general-purpose spaced-repetition library for any subject (data science, math, history, vocabulary, etc.). The core unit is a **Concept** (front/back/context/tags) grouped into **Topics**.

## Shell Commands

Never use compound shell commands with `cd && git` or `cd &&` chaining. Always use separate commands or `cd` first, then run the git/shell command independently.

## Project Configuration

Store project rules and preferences in project config files (e.g., `.claude/settings.json`, `CLAUDE.md`), NOT in memory files. Never save user instructions as memory files.

## Common Commands

**IMPORTANT**: Always use `uv run` to execute Python commands. Never run raw `python` commands.

```bash
# Install dependencies
uv sync

# Run unit tests
uv run pytest tests/ -v

# Run linter
uv run ruff check src/ tests/

# Run linter with auto-fix
uv run ruff check src/ tests/ --fix
```

## Versioning / Release

After version bumps, always stage and commit `uv.lock` along with the version change. Never forget the lock file.

## Testing

After any code change, run the full test suite and fix all failures before committing. Pay special attention to mock patching paths, fixture values, and assertion text that may need updating after refactors.

## Code Style

- Line length: 78 characters (enforced by ruff)
- Type hints required
- Docstring style: Sphinx/reST (`:param:`, `:return:`, `:raises:`)
- In docstrings, prefer single backticks (`` `name` ``) for inline code references
- **Do NOT use `from __future__ import annotations`** — the project requires Python >= 3.13, so PEP 604 union syntax (`X | Y`) and all modern annotation features work natively

## Conventions

- Example scripts use numeric prefixes for ordering: `01_`, `02_`, etc.
