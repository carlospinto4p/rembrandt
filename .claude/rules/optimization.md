# Periodic Optimization

Proactively suggest performance optimization opportunities in the
following situations:

## When to Suggest

1. **Every 6-7 versions released**: Same cadence as `/refactor` —
   suggest an optimization pass alongside refactoring reviews.

2. **During long sessions**: When a session involves multiple features
   or changes across several files, suggest optimizations before
   wrapping up.

3. **When noticing performance issues**: If you spot any of the
   following while working, flag them:
   - Unbounded data structures (lists, dicts, sets that grow without
     limit over long-running sessions)
   - O(n²) or worse patterns in hot paths
   - Unnecessary object copies or serialization

## What to Look For

- **Memory**: unbounded growth, large object retention, unnecessary
  copies, missing cleanup/eviction
- **CPU**: hot loops, redundant computation, expensive operations in
  tight paths, regex compiled per call
- **I/O**: missing connection reuse, redundant HTTP calls
- **Data structures**: lists used for lookups (should be sets/dicts),
  string concatenation in loops, repeated serialization
- **Pydantic**: unnecessary model copies, repeated validation,
  inefficient field access patterns

## How to Suggest

- Present findings as a prioritized list with file, line, and rationale
- Classify impact as HIGH / MEDIUM / LOW
- Don't auto-apply — always propose and let the user decide
- Group related findings (e.g., "DB query batching", "session memory")
- After each optimization proposal, add the items to `backlog.md`
  under a new section with the current date as the title (see
  `.claude/rules/backlog.md` for format)
