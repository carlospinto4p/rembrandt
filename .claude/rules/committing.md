---
name: committing
description: Git commit conventions and post-change workflow
version: 1.1
---

# Committing Guidelines

## Post-Change Workflow

**IMPORTANT**: After completing any task that involves code changes, ALWAYS follow this workflow:

1. **Run tests**: Execute `uv run pytest tests/unit -v` and ensure all tests pass
2. **Update tests if needed**: If the changes require test updates, fix them before committing
3. **Update version and changelog**: Follow `versioning.md` rules. Include guideline and tooling changes (`.claude/**`, `CLAUDE.md`) in the changelog too — **any** change under `.claude/` counts (rules, skills, commands, hooks, `settings.json`, etc.).
4. **Update README.md if needed**: When changes affect user-facing functionality:
   - New methods or classes: add usage examples
   - Changed method signatures or behavior: update existing examples
   - New configuration options: document them
5. **Update CLAUDE.md if needed**: When rules change or new important patterns emerge
6. **Sync lock file and reinstall**: Run `uv sync --all-extras` to update `uv.lock`. Only needed when `pyproject.toml` changed (version bumps, dependency changes, etc.). Note: `uv sync` may uninstall the editable install — if `uv run` fails afterwards, run `uv pip install -e ".[dev]"` to restore it.
7. **Commit changes**: Create a commit with a descriptive message following the format below
   - **Always include uv.lock** in commits when it has changed
8. **Push to remote**: Push the changes with `git push`

This workflow is MANDATORY after every prompt that results in code changes.

**Config/tooling changes** (anything under `.claude/` — rules,
skills, commands, hooks, `settings.json`, `settings.local.json` —
and `CLAUDE.md`): still require a patch version bump and changelog
entry, even when no application code changed. Follow the full
workflow above (skip tests only if no code changed). This applies
per project: if a cross-project migration touches N repos'
`.claude/` files, each repo gets its own patch bump and changelog
entry.

**Pure tracking changes** (`backlog.md` checkboxes only): commit and push,
but skip tests and version bump.

## When to Skip Tests

The default is to run tests (step 1). **Skip tests when the
staged diff consists exclusively of one or more of**:

- Markdown / docs (`*.md`, `changelog.md`, `README.md`)
- Version bump in `pyproject.toml`
- Lock file (`uv.lock`)
- `.claude/` config files (rules, skills, commands, hooks,
  `settings.json`, `settings.local.json`)
- `CLAUDE.md`

If **any** `.py` file is in the diff (including under
`tests/`), run tests. If the diff mixes a skippable file with
anything outside the list above, run tests. When in doubt, run
them — but do not launch a long suite for a one-line markdown
edit.

The signal is the diff itself, not your intent. Check
`git status --porcelain` before deciding.

## Commit Message Format

Use conventional commit style:

```
<type>: <description>

[optional body]
```

## Types

- `feat` - New feature or functionality
- `fix` - Bug fix
- `refactor` - Code refactoring without changing behavior
- `docs` - Documentation changes
- `test` - Adding or updating tests
- `chore` - Maintenance tasks, dependency updates

## Best Practices

- Keep the subject line under 72 characters
- Use imperative mood ("Add feature" not "Added feature")
- **Default to subject-only.** Skip the body unless it adds
  something a reader wouldn't get from the subject, the diff,
  and the changelog entry.
- Reference issues when applicable
- **One command per Bash call** — never chain git commands with `&&`,
  `;`, heredocs, or subshells. Each `git add`, `git commit`,
  `git push`, etc. must be its own separate Bash call.

## When to Add a Body

A body is warranted only when the *why* is non-obvious and not
already captured elsewhere. Good reasons:

- A workaround for a specific bug or upstream issue (link it)
- A hidden constraint that explains an unusual choice
- An incident or decision the diff alone won't surface

Do **not** write bodies that:

- Restate what the diff does
- Recap which version this is or how it relates to the previous one
- Describe a new file/skill/function in prose (the changelog does that)
- Add multi-paragraph design rationale that belongs in a PR description

If you do add a body, separate it from the subject with a blank line
and keep it tight — one short paragraph is almost always enough.

## Examples

```
feat: Add project registry with version tracking
```

```
fix: Handle missing changelog in cross-project sync
```

```
docs: Update README with installation options
```
