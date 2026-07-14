---
name: workbuddy-daily-credits
description: Claim WorkBuddy daily gift credits, check whether today's credits were claimed, or install/remove a zero-model daily schedule. Use for requests such as “领取今日积分”, “今天签到了吗”, “每天自动领 WorkBuddy 积分”, or reducing token/credit cost of an existing check-in automation.
---

# WorkBuddy Daily Credits

Use the bundled deterministic scripts. Do not use screenshots, OCR, mouse clicks, browser automation, or a model-generated substitute.

## Claim or inspect credits

Run exactly one command and return its compact result without extra analysis:

```bash
python3 "${CODEBUDDY_SKILL_DIR}/scripts/claim_daily_credit.py" --claim --json
```

For a status-only request, run:

```bash
python3 "${CODEBUDDY_SKILL_DIR}/scripts/claim_daily_credit.py" --status --json
```

The script reads WorkBuddy's current local login session, checks the desktop service status endpoint, and calls the claim endpoint only when needed. It never copies or prints tokens. This is an unofficial community integration and may need updates when WorkBuddy changes.

If the result is `AUTH_REQUIRED`, ask the user to open WorkBuddy and sign in, then retry once. Do not request or expose a token.

## Configure zero-model daily claiming

Prefer the macOS LaunchAgent because it runs the local script directly and consumes no model tokens or WorkBuddy task credits.

Install a daily schedule at 00:30:

```bash
python3 "${CODEBUDDY_SKILL_DIR}/scripts/install_launch_agent.py" --hour 0 --minute 30
```

Use a different time only when requested. After installation, advise disabling any older WorkBuddy model-based check-in automation to avoid duplicate runs and model charges.

Remove the schedule when requested:

```bash
python3 "${CODEBUDDY_SKILL_DIR}/scripts/install_launch_agent.py" --uninstall
```

## Boundaries

- Claim only the signed-in user's daily WorkBuddy gift.
- Never publish content, invite users, complete growth tasks, or pursue other rewards automatically.
- Never print, persist, transmit elsewhere, or ask for access/refresh tokens.
- Treat `ALREADY_CLAIMED` as success and do not retry.
- On network errors, allow the next scheduled run to retry; do not loop.
