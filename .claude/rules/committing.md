# Committing Guidelines

## Post-Change Workflow

**IMPORTANT**: After completing any task that involves code changes, ALWAYS follow this workflow:

1. **Fix tests if needed**: If the changes require test updates, fix
   them before committing (the `preCommit` hook will catch failures,
   but fixing upfront avoids wasted commit attempts).
2. **Update version and changelog**: Follow `versioning.md` rules. Include guideline changes (`.claude/rules/`, `CLAUDE.md`) in the changelog too.
3. **Update README.md if needed**: When changes affect user-facing functionality:
   - New methods or classes: add usage examples
   - Changed method signatures or behavior: update existing examples
   - New configuration options: document them
4. **Update CLAUDE.md if needed**: When rules change or new important patterns emerge
5. **Sync environment**: Run `uv sync --all-extras` to update `uv.lock`,
   then `uv pip install -e ".[dev]"` to reinstall the editable package.
6. **Commit changes**: Create a commit with a descriptive message following
   the format below.
   - **Always include `uv.lock`** in the commit — run `git status` to
     verify it is staged before committing.
   - Use simple `-m "..."` quoting for commit messages (no heredocs).
   - The `preCommit` hook will run tests; if they fail the commit is
     aborted — fix and retry.
7. **Tag the version**: Run `git tag vX.Y.Z` to create a tag for the
   new version.
8. **Push to remote**: Push the changes and tag with `git push` then
   `git push --tags`

This workflow is MANDATORY after every prompt that results in code changes.

**Guideline changes** (`.claude/rules/`, `CLAUDE.md`): still require a
patch version bump and changelog entry — follow the full workflow above
(skip tests only if no code changed).

**Pure tracking changes** (`backlog.md` checkboxes only): commit and push,
but skip tests and version bump.

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
- Separate subject from body with a blank line
- Use the body to explain *what* and *why*, not *how*
- Reference issues when applicable

## Examples

```
feat: Add spaced-repetition module

Added review() and select_words() for SM-2 scheduling.
```

```
fix: Handle missing progress in Session.answer()
```

```
docs: Add theory documentation for spaced repetition
```
