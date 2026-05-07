---
name: found-issues
description: Handle issues found mid-task — fix inline or add to backlog, never leave them unresolved
version: 1.0
---

# Handling Issues Found While Working

When you notice an issue, bug, inconsistency, or orphan
that is **not** part of the current task — in tool
output, health checks, drift reports, registry audits,
logs, grep hits, whatever — do not just flag it and
move on.

Every such finding must end in one of two outcomes:

1. **Fix it inline** if it is small, related, and safe
   to address without derailing the current task.
2. **Add it to `backlog.md`** as a new item (see
   `.claude/rules/backlog.md` for format) under the
   current date.

"Noted but left alone" is not an outcome. If you write
the phrase "pre-existing issue" or equivalent, decide
which bucket it goes in before the turn ends.

## Do not launder your own mistakes as pre-existing

Before labeling something "pre-existing," verify it
actually predates this session. If you introduced the
issue — directly or indirectly, e.g. through a sync,
edit, tool call, or reorganization earlier in this
conversation — own it and fix it. Do not use
"pre-existing" as a rhetorical dodge to avoid
responsibility for regressions you caused.

Check before labeling: recent git log, your own edits
this session, outputs of commands you ran. If in
doubt, investigate before claiming the issue is
unrelated to your work.
