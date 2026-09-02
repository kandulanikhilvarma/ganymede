# Security policy

Ganymede is a research prototype. It ships **no real borrower data** — the
repository uses public datasets (Freddie Mac, Home Credit) and synthetic
conversations. No secrets are committed; API keys live in a local, gitignored
`.env`.

## Reporting a vulnerability

Email **kandulanikhilvarma@gmail.com** with details and reproduction steps.
Please do not open a public issue for security-sensitive reports.

## Scope

- The models are trained on public data and are not fit for production lending
  decisions without a pilot (see `docs/CASE.md`).
- Any deployment handling real borrower data must add its own data-protection,
  retention, and consent controls — out of scope for this prototype.
