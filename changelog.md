
## Changelog - Rembrandt


### v6.3.69 - 28th July 2026

- Rotated changelog: archived 4 entries to `changelog/2026.md`.


### v6.3.68 - 27th July 2026

- Updated `.claude/rules/committing.md` from canonical: added a
  "Concurrent Sessions" section covering the cross-session
  commit-pollution hazard (check `git status --porcelain`
  immediately before every commit, stage by name, diff before
  re-shipping a change another session already committed).


### v6.3.67 - 26th July 2026

- Redeployed the hardened `scripts/changelog-add.sh`: guards against
  the CWD-relative wrong-repo footgun (comparing the target
  changelog's version against the wrong repo's manifest when invoked
  from outside its own directory).


### v6.3.66 - 25th July 2026

- Updated `.claude/rules/committing.md` from canonical: clarifies that
  a lock file's self-referential version drifting by a patch after a
  non-code bump is expected and harmless — not something to chase
  across repos.


### v6.3.65 - 25th July 2026

- Rotated changelog: archived 5 entries to `changelog/2026.md`.


### v6.3.64 - 24th July 2026

- `CLAUDE.md`: replaced the superseded **Core Rules** periodic-review
  trigger with the backlog-depth rule — when `/backlog` shows fewer
  than 5 open items, propose `/scan`, `/improvements`, and `/prune`.
  The old "Every 6-7 versions" cadence also named `/refactor` and
  `/optimize`, neither of which is a real skill. Pushed from the
  programme registry via `sync-config --types section`.


### v6.3.63 - 24th July 2026

- Updated `.claude/rules/committing.md`: adds the canonical
  `Pull First — Before Any Work` section — `git pull` is the first step
  of every session, run before reading, planning, or editing, not just
  before pushing. Synced from the programme registry (rule v1.4).


### v6.3.62 - 24th July 2026

- Updated `.claude/rules/committing.md` from canonical: `uv.lock` is
  committed whenever it changed, and a lock-only diff takes no version
  bump or changelog entry (bumping `pyproject.toml` would push it ahead
  again and recreate the drift, so it never converges).
- Committed the pending `uv.lock` self-referential version line, per
  that same rule — it had been left dirty on disk.


### v6.3.61 - 24th July 2026

- Updated `.pre-commit-config.yaml`: the ruff hooks now run
  `uv run --no-sync ruff` instead of `uvx ruff`.
  - `uvx` resolves whatever ruff PyPI serves that day, so the commit
    gate and this project's own lock-pinned ruff were different
    versions — and any upstream ruff release could change the enforced
    rule set with no local change. `uv run` uses this project's ruff,
    so local and commit-time linting always agree.
  - `--no-sync` is required, not an optimization: a bare `uv run`
    re-syncs first, which on a version-bump commit rewrites `uv.lock`
    mid-hook and leaves pre-commit's stash/restore cycle fighting its
    own linter. Verified in programme v4.83.1.
  - `ruff format` loses its `.` argument: pre-commit already passes the
    staged files, and a literal `.` overrode that to format the whole
    tree.
  - Pushed from programme's canonical `python-base` skeleton (v4.83.1).


### v6.3.60 - 10th July 2026

- Rotated changelog: archived 2 entries to `changelog/2026.md`.


### v6.3.59 - 4th July 2026

- Rotated changelog: archived 2 entries to `changelog/2026.md`.


### v6.3.58 - 3rd July 2026

- Updated `.pre-commit-scripts/check_version_changelog.sh` to canonical:
  exclude `reservations/**` placeholder manifests from version-bump
  detection, so defensive package-name holds don't demand a changelog
  entry (programme fleet rollout).


### v6.3.57 - 1st July 2026

- Rotated changelog: archived 1 entries to `changelog/2026.md`.


### v6.3.56 - 28th June 2026

- Rotated changelog: archived 1 entries to `changelog/2026.md`.


### v6.3.55 - 25th June 2026

- Rotated changelog: archived 1 entries to `changelog/2026.md`.


### v6.3.54 - 25th June 2026

- Rotated changelog: archived 5 entries to `changelog/2026.md`.


### v6.3.53 - 20th June 2026

- Added `scripts/changelog-add.sh` (safe changelog-prepend helper) and the `check-version-changelog` pre-commit guard, distributed in the programme fleet rollout.
- Restored `.pre-commit-scripts/check_unstaged_claude.py` and removed the
  stray `.pre-commit-scripts/` `.gitignore` entry so local hook scripts
  are tracked like the rest of the fleet.


### v6.3.52 - 20th June 2026

- `scripts/backup_db.py`: tightened the shrink guard to refuse **any**
  snapshot smaller than the existing backup (was a >50% collapse) — a
  smaller source signals truncation/data loss. The refusal exits
  non-zero so the backup unit's `OnFailure` handler raises the alarm;
  `--allow-shrink` overrides. Added a one-byte-smaller regression test.


### v6.3.51 - 20th June 2026

- `scripts/backup_db.py`: guard `backup_one` against clobbering a good
  Dropbox backup with empty/fresh-machine data — refuse a missing or
  zero-byte source, and refuse a snapshot under 50% of the existing
  backup unless `--allow-shrink`. Added `tests/unit/test_backup_db.py`
  (5 tests). Mirrors programme's `backup_guard`.


### v6.3.50 - 14th June 2026

- Added the `check-changelog-headers` pre-commit guard
  (`.pre-commit-scripts/check_changelog_headers.sh` + the `.pre-commit-config.yaml`
  stanza): blocks a changelog edit that overwrites an existing version
  header (the bug that silently lost manifold's `v0.1.35`).


### v6.3.49 - 13th June 2026

- Rotated changelog: archived 1 entries to `changelog/2026.md`.


### v6.3.48 - 13th June 2026

- Rotated changelog: archived 1 entries to `changelog/2026.md`.


### v6.3.47 - 10th June 2026

- Rotated changelog: archived 2 entries to `changelog/2026.md`.


### v6.3.46 - 8th June 2026

- Synced from programme: reworded `versioning.md` changelog-prepend guidance (insert a new entry above the top header, never replace it) and added universal `.gitignore` entries (`*.bak.*`, `*.tmp.*`, etc.).


### v6.3.45 - 7th June 2026

- Rotated changelog: archived 1 entries to `changelog/2026.md`.


### v6.3.44 - 4th June 2026

- Rotated changelog: archived 6 entries to `changelog/2026.md`.


### v6.3.43 - 4th June 2026

- Synced `.claude/rules/committing.md` from the programme registry: step 6 now scopes `uv.lock` regeneration to code-related bumps only — non-code patch bumps (`.claude/` config, docs, changelog, rule syncs) skip `uv lock`.


### v6.3.42 - 3rd June 2026

- Synced `.claude/rules/testing.md` from the programme registry: added the SQLite-backed fixtures pointer to the session-scoped template pattern (see the shared `testing-python` rule).


### v6.3.41 - 1st June 2026

- Updated `.claude/rules/committing.md`: no-parallel-git-command rule and `-m` flag guidance.


### v6.3.40 - 31st May 2026

- Added `[build-system]` to `pyproject.toml`; `uv sync --all-extras` now handles the editable install automatically.
