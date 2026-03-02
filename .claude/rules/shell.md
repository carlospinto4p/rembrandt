# Shell Command Guidelines

## Keep commands simple

Prefer one simple command per Bash tool call. Compound commands
(`&&` chains, pipes, subshells) trigger extra permission prompts
that interrupt the session.

**Do:**
```bash
git add file1.py file2.py
```
```bash
git commit -m "feat: Add feature (v1.2.0)"
```
```bash
git push
```

**Don't:**
```bash
cd /some/path && git add . && git commit -m "msg" && git push
```

## No `cd` prefix

The working directory is already set to the project root.
Do not prefix commands with `cd /path &&`.

## Always use `uv run` for Python

Never run raw `python` or `pytest` commands. Always prefix with
`uv run`:

```bash
uv run pytest tests/unit -v
uv run ruff check src/ tests/
```

## Output redirection

The shell is MSYS bash on Windows. Use Unix-style redirection
(`/dev/null`, not `NUL`).

## Git commands

- Use plain `git` commands with simple `-m "..."` quoting.
- Do not use heredocs for commit messages.
