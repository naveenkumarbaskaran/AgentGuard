#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYPROJECT="$REPO/pyproject.toml"
INIT="$REPO/agentguard/__init__.py"
CURRENT=$(grep '^version = ' "$PYPROJECT" | sed 's/version = "\(.*\)"/\1/')
echo "Current version: $CURRENT"
BASE=$(echo "$CURRENT" | sed 's/[ab][0-9]*$//' | sed 's/rc[0-9]*$//')
MAJOR=$(echo "$BASE" | cut -d. -f1); MINOR=$(echo "$BASE" | cut -d. -f2); PATCH=$(echo "$BASE" | cut -d. -f3)
BUMP="${1:-patch}"
case "$BUMP" in
  major) NEW="$((MAJOR+1)).0.0" ;;
  minor) NEW="${MAJOR}.$((MINOR+1)).0" ;;
  patch) NEW="${MAJOR}.${MINOR}.$((PATCH+1))" ;;
  [0-9]*) NEW="$BUMP" ;;
  *) echo "Usage: $0 [major|minor|patch|X.Y.Z]"; exit 1 ;;
esac
echo "New version: $NEW"
read -p "Bump $CURRENT → $NEW? [y/N] " -n 1 -r; echo ""
[[ ! $REPLY =~ ^[Yy]$ ]] && echo "Aborted." && exit 0
sed -i '' "s/^version = \"${CURRENT}\"/version = \"${NEW}\"/" "$PYPROJECT"
sed -i '' "s/__version__ = \"${CURRENT}\"/__version__ = \"${NEW}\"/" "$INIT"
git -C "$REPO" add "$PYPROJECT" "$INIT"
git -C "$REPO" commit -m "chore: bump version $CURRENT → $NEW"
git -C "$REPO" tag "v${NEW}"
echo "✓  git commit + tag v${NEW}"
echo "  Next: git push origin main --tags"
