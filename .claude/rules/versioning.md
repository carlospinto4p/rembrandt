# Versioning Workflow

As part of the commit workflow (step 3 in `committing.md`), update the version and changelog before committing. Ask the user which version type (major/minor/patch) if unclear.

**Important: One feature per version release.** Each new feature gets its own version release. Do NOT combine multiple features into a single version, even if implemented in the same session. This keeps the changelog clean and makes it easier to track what changed in each version.

**Version scheme** (semantic versioning):
- `MAJOR.0.0` - Breaking changes (removed/renamed modules, changed dependencies, API changes that break existing code)
- `MAJOR.MINOR.0` - New modules, significant features, or substantial enhancements (backward compatible)
- `MAJOR.MINOR.PATCH` - Bug fixes, small improvements, tests, documentation

**Minor version indicators** (use MINOR bump when):
- Adding new public methods or classes
- Significantly expanding existing functionality (e.g., adding many new fields to outputs)
- Adding new optional features or configuration options
- Structural improvements that enhance usability

**Breaking changes** that require a major version bump:
- Removing or renaming public modules, classes, or functions
- Changing required dependencies (e.g., making a dependency optional)
- Changing method signatures in incompatible ways
- Removing features or changing default behavior

**Files to update:**
1. `pyproject.toml` - Update the `version` field
2. `changelog.md` - Add entry at the top following the format below

**Changelog format — keep it concise:**
```markdown
### vX.Y.Z - DDth Month YYYY

- Added enums in `module_name`:
  - `EnumA`
  - `EnumB`
- Added `ClassName.method_name()`: brief description.
- Updated `ClassName`: brief description of what changed.
```

**Style rules:**
- Do not add "Breaking change" labels or bold markers — the major version
  bump already signals that. Just describe what changed.
- Use short action verbs: "Added", "Updated", "Fixed", "Removed".
- Name the class/method/enum directly — no need to repeat the full module
  path for every sub-item or spell out base classes and enum values.
- One bullet per logical change. **When listing 3+ items** (enums, methods,
  files, etc.), **always use sub-bullets** — never inline them in a
  comma-separated list or parenthetical group. This applies everywhere:
  removed symbols, added methods, updated files, etc.
  ```markdown
  # BAD — inlined in parentheses:
  - Removed re-exports (`Foo`, `Bar`, `Baz`, `Qux`).

  # GOOD — sub-bullets:
  - Removed re-exports:
    - `Foo`
    - `Bar`
    - `Baz`
    - `Qux`
  ```
- **Group by folder**: When multiple files in the same directory are changed,
  group them under one bullet with sub-bullets per file:
  ```markdown
  - Updated `.claude/rules/`:
    - `testing.md`: Fixed test paths.
    - `committing.md`: Collapsed versioning sub-bullets.
  ```

**IMPORTANT**: Always leave **two blank lines** between version entries in the changelog for readability.
