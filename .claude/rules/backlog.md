# Backlog Management

The `backlog.md` file tracks all improvements, fixes, and refactoring proposals.

## Format

- **Use checkboxes** (`- [ ]` / `- [x]`) for every item
- **Organize by date/version**, not by priority — each section header is a
  date with an optional version reference (e.g., `### 2026.02.09 (v1.10.3 refactor review)`)
- **Do not split by priority categories** (no "High/Medium/Low" subsections)
- Mark items as done (`- [x]`) when completed
- **Always mark backlog items as done** (`- [x]`) immediately after
  completing the corresponding task — do not wait for the user to ask

## Displaying the Backlog

- **When showing the backlog to the user** (e.g., to choose tasks), display
  each item with a sequential number to make it easy to pick tasks by number

## Workflow Rules

When the user says "implement items X, Y, Z" or "do backlog items N-M",
implement them sequentially — commit each one, then move to the next.
Do not plan all of them upfront.
