#!/bin/bash
# Run tests before git commit commands.
# Hooks receive JSON on stdin with tool_input.command.
COMMAND=$(python -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('command', ''))
")

if echo "$COMMAND" | grep -q 'git commit'; then
    uv run pytest tests/ --tb=short -q
fi
