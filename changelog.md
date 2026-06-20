
## Changelog - Rembrandt


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


### v6.3.39 - 31st May 2026

- Added `scripts/backup_db.py`: snapshots `data_science.db` to
  `~/Dropbox/home/development/db/rembrandt/` using the SQLite online
  backup API (atomic write; source opened read-only). Destination
  overridable via `REMBRANDT_BACKUP_DEST` env var or `--dest` flag.


### v6.3.38 - 17th May 2026

- Rotated changelog: archived 5 old entries to `changelog/2026.md`.


### v6.3.37 - 9th May 2026

- Added `When to Skip Tests` section to `.claude/rules/committing.md`: explicit allowlist (markdown, version bump, lock file, `.claude/` config, `CLAUDE.md`) of diffs where tests can be safely skipped.


### v6.3.36 - 9th May 2026

- Regrouped 2 historical changelog entries flagged by `/changelog-review` (programme v2.52.143):
  - `changelog/2026.md` v0.27.1: 3 bullets touching `db.py` collapsed under one parent.
  - `changelog/2026.md` v0.9.0: 3 bullets touching `scripts/` collapsed under one parent.


### v6.3.35 - 9th May 2026

- Updated `.claude/rules/versioning.md` (1.0 → 1.1): rewrote changelog-format section to fix rule/example contradiction; threshold now stated as "3+ top-level bullets touching the same module → group under a parent"; sub-bullet patterns reorganised; added "When NOT to group" section. Synced from programme v2.52.144.


### v6.3.34 - 8th May 2026

- Synced canonical rules from `programme` v2.52.139/v2.52.140: `backlog`, `refactoring`, `optimization`, `improvements` rules promoted to global (`~/.claude/rules/`) and removed locally; `versioning.md` updated with depth-based-cadence batch exception.


### v6.3.33 - 2nd May 2026

- Rotated changelog: archived 2 entries to , keeping 30.


### v6.3.32 - 26th April 2026

- Updated `.claude/rules/committing.md`: remove SKIP workaround, ruff now runs via `uv run ruff` in all projects.


### v6.3.31 - 26th April 2026

- Updated `.claude/rules/committing.md`: add Windows `SKIP=ruff-format,ruff-fix` pattern for pre-commit hook failures when ruff is not in PATH.


### v6.3.30 - 20th April 2026

- Synced canonical `.gitignore` from programme (direnv block).


### v6.3.29 - 20th April 2026

- Synced canonical `.claude/rules/*.md` from programme.


### v6.3.28 - 19th April 2026

- Added `scripts/pre-commit.sh`: canonical pre-commit check from programme. Auto-detects `tests/unit/` vs `tests/` and no-ops if neither exists.


### v6.3.27 - 17th April 2026

- `.gitattributes`: Added LF line ending normalization.


### v6.3.26 - 15th April 2026

- `.claude/`: cross-project migration landed today:
  - Removed `.claude/hooks/block-raw-python.sh`; now provided globally at `~/.claude/hooks/` (PreToolUse Bash guard).
  - Removed `.claude/hooks/block-chained-commands.sh` and `.claude/skills/{refactor,improvements,optimize,self-refinement,backlog}/`; the hook and the five periodic-review skills are now provided globally under `~/.claude/`.
  - Removed `.claude/hooks/format-python.sh`; the ruff auto-format PostToolUse hook is now provided globally at `~/.claude/hooks/`.
  - Removed `.claude/hooks/pre-commit-tests.sh`; replaced by a global dispatcher at `~/.claude/hooks/pre-commit-tests.sh` that invokes `scripts/pre-commit.sh` on `git commit`. Added `scripts/pre-commit.sh` with the project-local test command.


### v6.3.25 - 12th April 2026

- Updated `.claude/hooks/block-chained-commands.sh`:
  propagated newline-chaining block from the
  programme canonical.


### v6.3.24 - 11th April 2026

- `.claude/rules/`:
  - Decoupled `/refactor` rule: canonical
    `refactoring.md` is now procedural only.
  - Added `refactoring-areas.md` with
    project-specific code smells to watch.
- `.claude/skills/refactor/`:
  - Updated `SKILL.md` to read both canonical
    procedure and per-project areas.


### v6.3.23 - 11th April 2026

- `.claude/rules/`:
  - Decoupled `/optimize` rule: canonical
    `optimization.md` is now procedural only.
  - Added `optimization-areas.md` with
    project-specific performance areas.
- `.claude/skills/optimize/`:
  - Updated `SKILL.md` to read both canonical
    procedure and per-project areas.


### v6.3.22 - 10th April 2026

- `.claude/rules/`:
  - Decoupled `/improvements` rule: canonical
    `improvements.md` is now procedural only.
  - Added `improvement-areas.md` with
    project-specific areas to watch.
- `.claude/skills/improvements/`:
  - Updated `SKILL.md` to read both canonical
    procedure and per-project areas.


### v6.3.21 - 5th April 2026

- `.claude/rules/`:
  - Updated `versioning.md`: added changelog
    rotation section (30-version limit, yearly
    archives in `changelog/YYYY.md`).


### v6.3.20 - 5th April 2026

- `.claude/rules/`:
  - Updated `versioning.md`: added changelog
    rotation section (30-version limit, yearly
    archives in `changelog/YYYY.md`).


### v6.3.19 - 5th April 2026

- Rotated changelog: archived 115 old
  entries to `changelog/` yearly files.
