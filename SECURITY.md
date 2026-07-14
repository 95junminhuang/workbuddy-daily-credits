# Security Policy

## Credential handling

The script reads the existing WorkBuddy desktop session at runtime. It does not copy the session file, persist tokens, or include tokens in normal output.

Requests carrying credentials are restricted to HTTPS and the exact host `copilot.tencent.com`. Do not remove this restriction without understanding the credential-exfiltration risk.

## Reporting a vulnerability

Open a GitHub issue containing only a minimal, redacted reproduction. Never attach:

- WorkBuddy authentication files
- access or refresh tokens
- unredacted application logs
- personal account identifiers

If a public issue would expose a credential or a working exploit, use GitHub's private vulnerability reporting feature when it is available for the repository.
