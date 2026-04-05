#!/bin/bash
# Run unit tests before git commit commands.
# Hooks receive JSON on stdin with tool_input.command.
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('command', ''))
")

if echo "$COMMAND" | grep -q 'git commit'; then
    uv run pytest tests/unit/ --tb=short -q
fi
