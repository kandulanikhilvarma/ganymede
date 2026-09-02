# Security policy

Ganymede ships **no real borrower data**. The repository builds on public
datasets (Freddie Mac, Home Credit) and synthetic conversations. No secrets are
committed, and API keys live in a local, gitignored `.env`.

## Reporting a vulnerability

Email **kandulanikhilvarma@gmail.com** with details and reproduction steps.
Please do not open a public issue for security-sensitive reports.

## Scope

- Model outputs are **advisory**. Every decision is logged with its experiment
  arm and propensity, which is what makes a recommendation auditable after the
  fact rather than a black box.
- The models are trained on public data. Any deployment against a real book
  starts in shadow mode, where the system shows nothing to anyone and is scored
  against the queue that was actually worked. See
  [the argument](https://ganymede-kandula.vercel.app/case).
- Any deployment handling real borrower data must add its own data-protection,
  retention and consent controls. Those are specific to the operator and are
  not shipped here.
