#!/usr/bin/env bash
# Prepend a new version entry to changelog.md SAFELY — the mechanical fix for
# the recurring "overwrite-prepend" mistake (a hand-edit that replaces the top
# `### vX.Y.Z` header instead of inserting above it, orphaning that version's
# bullets under the new entry; see .pre-commit-scripts/check_changelog_headers.sh
# and .claude/rules/changelog-entries.md).
#
# It NEVER edits an existing header: the new block is spliced in immediately
# BEFORE the first `### vX.Y.Z` line, so every prior header is only shifted down.
# That makes the overwrite bug structurally impossible — which a careless Edit
# can't promise.
#
# Usage:
#   scripts/changelog-add.sh <version> [date] <<'EOF'
#   - **Headline.** Body of the entry (one or more bullets / lines).
#   EOF
#
#   <version>  e.g. v0.1.107 (a leading 'v' is added if you omit it)
#   [date]     optional; defaults to today as "Dth Month YYYY" (e.g. "20th June
#              2026"), matching the existing entries. Forced to the C locale so
#              the month name is English regardless of the shell locale.
#   body       read from stdin (heredoc or a pipe). Required, non-empty.
#
#   -f, --file PATH   changelog to edit (default: ./changelog.md)
#
# The body is inserted verbatim — write it exactly as it should appear
# (leading "- " bullets, wrapped lines, etc.). The version you pass should match
# the manifest bump in the same commit; the `check-version-changelog` guard
# enforces that at commit time.
set -euo pipefail

file="changelog.md"
args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--file) file="$2"; shift 2 ;;
    -h|--help) sed -n '2,33p' "$0"; exit 0 ;;
    -*) echo "Unknown option: $1" >&2; exit 2 ;;
    *) args+=("$1"); shift ;;
  esac
done

if [[ ${#args[@]} -lt 1 || ${#args[@]} -gt 2 ]]; then
  echo "usage: scripts/changelog-add.sh <version> [date] < body" >&2
  exit 2
fi

version="${args[0]}"
[[ "$version" == v* ]] || version="v$version"
if [[ ! "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Bad version '$version' — want vMAJOR.MINOR.PATCH (e.g. v0.1.107)." >&2
  exit 2
fi

if [[ ${#args[@]} -eq 2 ]]; then
  date_str="${args[1]}"
else
  day="$(LC_ALL=C date +%-d)"
  case "$day" in
    1|21|31) suf=st ;;
    2|22) suf=nd ;;
    3|23) suf=rd ;;
    *) suf=th ;;
  esac
  date_str="${day}${suf} $(LC_ALL=C date +'%B %Y')"
fi

[[ -f "$file" ]] || { echo "No changelog at '$file'." >&2; exit 1; }

# Body from stdin; command substitution trims trailing newlines so we control
# the spacing exactly.
body="$(cat)"
[[ -n "$body" ]] || { echo "Empty body on stdin — nothing to add." >&2; exit 2; }

# Refuse to add a header that already exists (a duplicate would be a separate
# kind of mess). Match the version token at a header line start.
if grep -qE "^### ${version} " "$file"; then
  echo "$version already has a changelog header — refusing to duplicate." >&2
  exit 1
fi

# The splice point: the first existing version header. Everything before it
# (title + blank gap) is kept as-is; the new block goes in just above it, so no
# existing header is ever touched. If there is no header yet, append after the
# whole file.
hdr_line="$(grep -nE '^### v[0-9]+\.[0-9]+\.[0-9]+' "$file" | head -1 | cut -d: -f1 || true)"

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
if [[ -n "$hdr_line" ]]; then
  head -n "$((hdr_line - 1))" "$file" >"$tmp"
  printf '### %s - %s\n\n%s\n\n\n' "$version" "$date_str" "$body" >>"$tmp"
  tail -n "+$hdr_line" "$file" >>"$tmp"
else
  # No prior entries: keep the title block, then the new entry.
  cat "$file" >"$tmp"
  printf '\n### %s - %s\n\n%s\n' "$version" "$date_str" "$body" >>"$tmp"
fi
mv "$tmp" "$file"
trap - EXIT

echo "Added '### $version - $date_str' to $file (above the previous top entry)."
