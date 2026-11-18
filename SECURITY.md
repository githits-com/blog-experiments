# Security Policy

## Reporting a vulnerability

Please do not open a public issue for a security problem. Use GitHub's
private vulnerability reporting for this repository ("Report a vulnerability"
under the Security tab). If that option is unavailable, email
[security@githits.com](mailto:security@githits.com), the contact published in
[GitHits' security reporting guidance](https://githits.com/legal/terms-of-service/).
Include the affected version, impact, and a minimal reproduction without tokens
or private repository contents. We acknowledge reports within five business days.

## What this repository holds

This repository is the code behind GitHits blog posts: harnesses, analysis
scripts, and design notes. Runs talk to third-party sandbox APIs using
credentials supplied only through environment variables. Do not commit tokens,
result files, logs, or sandbox identifiers.

## Supported versions

Only the latest commit on `main` receives fixes.
