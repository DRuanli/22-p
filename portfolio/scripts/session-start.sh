#!/bin/bash
# Runs on every Claude Code session start (local and cloud).
# Installs deps only in cloud sessions, and only when missing.
if [ "$CLAUDE_CODE_REMOTE" != "true" ]; then
  exit 0
fi
cd "$CLAUDE_PROJECT_DIR" || exit 0
if [ -f package.json ] && [ ! -d node_modules ]; then
  npm ci || npm install || true
fi
# Playwright's Chromium (needs cdn.playwright.dev + playwright.download.prss.microsoft.com
# in the environment's allowed domains; see README step 2)
if [ -d node_modules/playwright ] && [ ! -d "$HOME/.cache/ms-playwright" ]; then
  npx playwright install --with-deps chromium >/dev/null 2>&1 || true
fi
exit 0
