#!/usr/bin/env bash
# Push a branch, rebasing onto its remote head between attempts.
#
# Several workflows write to the same branch (update-version-metadata and
# update-changelog both commit to test), so a bare push loses the race whenever
# another run pushes first:
#
#   ! [remote rejected] test -> test (cannot lock ref 'refs/heads/test':
#       is at 712bd70... but expected 4dae454...)
#
# usage: push_with_retry.sh <branch> [attempts]
set -euo pipefail

BRANCH="${1:?usage: push_with_retry.sh <branch> [attempts]}"
ATTEMPTS="${2:-3}"

for attempt in $(seq 1 "$ATTEMPTS"); do
  if git push origin "$BRANCH"; then
    echo "✅ Pushed $BRANCH (attempt $attempt/$ATTEMPTS)"
    exit 0
  fi
  echo "⚠️  Push to $BRANCH failed (attempt $attempt/$ATTEMPTS); rebasing onto origin/$BRANCH"
  git pull --rebase origin "$BRANCH"
done

echo "❌ Could not push $BRANCH after $ATTEMPTS attempts"
exit 1
