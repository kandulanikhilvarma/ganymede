# Phase 8 — evals

One command prints the metric table and writes a dated report. What is measurable
now is measured; what needs the randomised pilot is marked pending, never faked.

```
python -m ganymede.evals.report --report
```

## Judge reliability (Krippendorff's alpha)

The method from the plan's risk research: put the judge in the annotator pool and
test whether it agrees with the human like a second coder would, against the
intra-rater ceiling.

| Metric | Value |
|---|---|
| Judge vs human agreement | **0.917** (target 0.60 — your bar) |
| Within-judge alpha (ceiling) | 1.0 |
| Mixed-pool alpha | 0.886 |
| Ceiling ok (not fitting noise) | **yes** — 0.886 ≤ 1.0 |

Mixed-pool alpha sitting at or below the within-judge ceiling means the judge
behaves like a genuine second coder agreeing with judgment, not with itself —
the SCHUFA-style self-agreement failure the plan warned about does not occur.

## The metric table

| Metric | Status |
|---|---|
| Hint usefulness (0.917) | measured |
| Judge reliability (alpha 0.886) | measured |
| Risk calibration (L1 Brier < base) | measured (Phase 3) |
| Recovery per agent-hour | **pilot required (I1/I2)** |
| PTP-kept lift | **pilot required (I1)** |
| Override rate | **pilot required (live traffic)** |

The three pending rows are the honest boundary: they need the randomised control
arm and real traffic. `lift_on_set` enforces I1 in code — it refuses to compute a
lift number on any set containing synthetic records.

## Drift monitors (I12)

- **PSI** on continuous score/feature distributions: <0.1 stable, 0.1-0.25
  moderate, >0.25 alert.
- **Rate drift** for binary outcomes: PSI underweights a base-rate shift on 0/1
  labels, so the self-cure drift found in Phase 3 (0.60 -> 0.72) is watched by a
  direct rate-delta monitor instead. Honest about the tool's limits rather than
  reporting a stable PSI on a drift that is real.
