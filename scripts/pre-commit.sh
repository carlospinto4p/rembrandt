#!/bin/bash
# Project-local pre-commit checks. Invoked by the global
# ~/.claude/hooks/pre-commit-tests.sh when a Bash tool runs
# `git commit`. Exit non-zero to block the commit.
set -e

if [[ -d "tests/unit" ]]; then
    TEST_PATH="tests/unit/"
elif [[ -d "tests" ]]; then
    TEST_PATH="tests/"
else
    echo "pre-commit.sh: no tests directory found; skipping." >&2
    exit 0
fi

uv run pytest "$TEST_PATH" --tb=short -q
