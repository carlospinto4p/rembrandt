---
name: versioning
description: Semantic versioning scheme, changelog format, and release workflow
version: 1.1
---

# Versioning Workflow

After making significant changes, proactively update the version and changelog as part of the commit workflow. Ask the user which version type (major/minor/patch) if unclear.

**Important: One feature per version release.** Each new feature gets its own version release. Do NOT combine multiple features into a single version, even if implemented in the same session. This keeps the changelog clean and makes it easier to track what changed in each version.

**Exception — periodic-pass batches**: When implementing items from a single periodic pass (`/scan`, `/improvements`, or `/prune`), small related items in the same finding category (e.g. several "Memory" findings from one scan) can share a single commit and patch version. Independent features still get their own version. The grouping unit is the finding category, not the entire backlog dump — this prevents version drift after a 60-item scan.

**Version scheme** (semantic versioning):
- `MAJOR.0.0` - Breaking changes (removed/renamed modules, changed dependencies, API changes that break existing code)
- `MAJOR.MINOR.0` - New modules, significant features, or substantial enhancements (backward compatible)
- `MAJOR.MINOR.PATCH` - Bug fixes, small improvements, tests, documentation

**Minor version indicators** (use MINOR bump when):
- Adding new public methods or classes
- Significantly expanding existing functionality
- Adding new optional features or configuration options
- Structural improvements that enhance usability

**Breaking changes** that require a major version bump:
- Removing or renaming public modules, classes, or functions
- Removing or replacing required dependencies
- Changing method signatures in incompatible ways
- Removing features or changing default behavior

**Files to update:**
1. `pyproject.toml` - Update the `version` field
2. `changelog.md` - Add entry at the top following the format below

**Changelog format:**

Each version is a top-level bullet list. **When 3+ top-level
bullets would touch the same file or directory, group them under
a single parent bullet for that module** — do not repeat the
path across siblings. With 1–2 same-module bullets, keep them
flat with the path inline.

```markdown
### vX.Y.Z - DDth Month YYYY

- Added `src/programme/release.py`:
  - `BumpResult`: dataclass.
  - `Bumper`: base class.
  - `PythonBumper`, `KotlinBumper`, `NoneBumper`: language handlers.
- Added `tests/unit/test_release.py`: 16 dispatch tests.
- Closes the gap surfaced earlier today: cross-project commit
  scripts now branch on `Project.language`.
```

The grouped form makes the scope readable at a glance and removes
path repetition. Narrative bullets (decisions, motivation,
cross-project context) stay flat — they have no module to group
by.

**Style rules:**

- Use single backticks (`` `name` ``) for inline code — never
  double backticks.
- Do not add "Breaking change" labels or bold markers — the major
  version bump already signals that. Just describe what changed.
- Use short action verbs: "Added", "Updated", "Fixed", "Removed".
- Name the class/method/enum directly — no need to repeat the
  full module path for every sub-item.
- One bullet per logical change. **When listing 3+ items inside a
  parent** (enums, methods, files, etc.), use sub-bullets — never
  inline them in a comma-separated list.

**Sub-bullet patterns** (each derives from the 3+ shared-module
rule above):

- **Same file** — multiple changes to one file:
  ```
  - `db/utils.py`:
    - Added `create_db()`.
    - Added `require_db()`.
    - Added `dump_db()`.
  ```
- **Same directory** — multiple files in one directory:
  ```
  - Added unit tests:
    - `tests/test_base.py`: 22 tests.
    - `tests/test_tables.py`: 12 tests.
    - `tests/test_drift.py`: 14 tests.
  ```
- **Cascade** — a parent change with downstream consequences:
  ```
  - Moved `app/` into `src/project/app/`:
    - Updated `Dockerfile` entrypoint.
    - Updated `README.md` run command.
    - Updated `docker-compose.yml` volume.
  ```

**When NOT to group:**

- 1- or 2-item changes touching the same module — keep flat with
  the path inline:
  ```
  - Added `docs/schema.md`: ERD and schema documentation.
  - Updated `src/foo.py` and `src/bar.py`: shared error class.
  ```
- Unrelated changes — separate top-level bullets.
- Narrative bullets without a file reference — flat at top level.

**IMPORTANT**: Always leave **two blank lines** between version entries in the changelog for readability.

**IMPORTANT**: Always include changes under `.claude/` (rules, skills, commands, hooks, `settings.json`, `settings.local.json`) and `CLAUDE.md` in the changelog, and bump at least a patch version. These are project configuration/tooling changes that affect development workflow and must be tracked like any other change. Cross-project migrations that modify each repo's `.claude/` files require a patch bump per repo, not just in the project that drove the migration.

## Reading the Changelog

**Never read the full changelog.** It wastes tokens.

- **To add a new entry**: read only the first 5 lines
  (`limit: 5`) to find the header, then prepend after it.
- **To find a specific entry**: use Grep with the version
  or keyword — never read the whole file to search.
- **To count versions** (e.g., for periodic pass cadence):
  use Grep with pattern `^### v` in `count` mode.

## Changelog Rotation

`changelog.md` holds only the **last 30 versions**. Older
entries live in `changelog/YYYY.md` yearly archive files.

- **Always add new entries to `changelog.md`** — never
  write directly to archive files.
- **Do not read archive files directly** — they can be
  very large. If you need to find an old entry, use
  Grep on the archive files or ask the user.
- **Rotation happens periodically** via
  `/rotate-changelog`. You do not need to rotate manually
  after each version bump — just keep adding to
  `changelog.md`.
