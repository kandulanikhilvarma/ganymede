# Ganymede — Recovery Intelligence System

Risk + coaching over one loop, for lending, receivables, and investor-funded
credit books. Risk Lens decides who to contact, when, and with what offer.
Coach Lens shapes the conversation. The outcome of that conversation is the
label that retrains both.

Full design: `../piped-coalescing-sundae.md` (plan) and `docs/`.

## Layout

```
ganymede/       models, allocator, coach, evals, monitors
app/            Next.js agent desk (Phase 9)
docs/           defects.md, status.md, rubric.md
tests/          invariant + component tests
```

## Run

```bash
pip install -e ".[dev]"
python -m ganymede.invariants --check   # I1-I14, static
python -m pytest -q
```

## Invariants

The design's 14 constraints (I1-I14) are enforced, not documented. See
`ganymede/invariants.py` and the plan's Design Invariants section. A defect is
closed when a check fails if it comes back — never before.

## Phase status

`docs/status.md`. Strictly sequential: no phase starts until the previous
phase's gate is green.
