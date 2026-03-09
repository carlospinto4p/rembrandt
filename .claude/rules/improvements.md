# Periodic Improvements

Proactively suggest new capabilities, features, and design
improvements for the library.

## When to Suggest

1. **When the backlog runs low**: If the backlog has fewer than
   3-4 open items, suggest an `/improvements` pass to replenish
   it with fresh ideas. Check the backlog after completing tasks.

2. **During long sessions**: When wrapping up a session with
   multiple completed tasks, suggest improvements before finishing.

3. **When noticing gaps**: If you spot any of the following while
   working, flag them:
   - Missing features that users of similar libraries would expect
   - Capabilities implied by the architecture but not yet exposed
   - Integration opportunities (new providers, export formats, etc.)
   - Developer experience improvements (better errors, logging,
     debugging tools)
   - Missing convenience methods or shortcuts for common patterns

## What to Look For

- **Exercise types**: new drill formats that reinforce vocabulary
  acquisition (listening, writing prompts, image association, etc.)
- **Spaced repetition**: scheduling refinements, analytics,
  alternative algorithms (FSRS, Leitner)
- **Content pipeline**: new language pairs, corpus importers,
  frequency-list builders, CEFR auto-tagging
- **Session features**: adaptive difficulty, streaks/gamification,
  progress visualisation helpers
- **Database / persistence**: export formats, backup utilities,
  migration tooling, multi-backend improvements
- **Developer experience**: better type hints, richer model
  representations, validation helpers, logging
- **Documentation**: missing examples, incomplete docstrings,
  outdated guides

## How to Suggest

- Present suggestions as a prioritized list with clear rationale
- Classify by impact (HIGH / MEDIUM / LOW) and effort
- Don't auto-apply — always propose and let the user decide
- Group related suggestions (e.g., "provider support",
  "developer experience", "new agent types")
- After each proposal, add the items to `backlog.md` under a new
  section with the current date as the title (see
  `.claude/rules/backlog.md` for format)
