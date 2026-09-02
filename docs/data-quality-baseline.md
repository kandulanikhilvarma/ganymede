# Data-quality baseline. Phase 2

Freddie Mac Single-Family Loan-Level, sampled panel. What the data supports,
and what it does not. Honest limits stated so Phase 3 does not overclaim.

## Shape

- **1,403,871** monthly rows, **87,845** loans, **9** vintages (2024Q1–2026Q1)
- Real calendar dates: 2024-01 → 2026-03 (clears I13, timing features are legal on this source)
- Zero missingness on core static features (credit_score, dti, cltv, orig_ltv) and monthly UPB

## Delinquency ladder, the signal the Risk Lens learns from

| Bucket (months) | Rows |
|---|---|
| 0 current | 1,135,761 |
| 1 (30–59d) | 158,976 |
| 2 (60–89d) | 35,738 |
| 3 (90d) | 17,381 |
| 4 | 11,956 |
| 5 | 9,061 |
| 6–12 | ~20,000 |
| 13–25 | ~3,400 |
| 99 (REO / terminal) | 966 |
| unknown (XX, too-new) | 10,306 |

The full roll curve is present, accounts move current → 30 → 60 → 90 → charge-off,
and also cure back. That transition structure is exactly what L1 trains on.

## Sampling, read before trusting any base rate

The sample **oversamples delinquency on purpose**. Every ever-delinquent loan is
kept; current loans are downsampled to fill the per-quarter quota. Result:
81,847 of 87,845 loans are ever-delinquent, nothing like the population, where
delinquency is rare.

**`sample_weight`** (1.0 for kept delinquents, up to ~236× for downsampled current
loans) recovers population proportions. **Phase 3 must apply it** for calibration,
or every predicted probability will be wildly too high. This is recorded, not
assumed, the same discipline the decision log applies to propensity.

Older vintages carry more months and more delinquency (loans have aged);
2026Q1 is a fresh vintage, mostly `XX`/current with little history yet. Vintage
stratification at model time matters, a model trained only on aged 2024 loans
learns a different world from the 2025 book.

## What this data cannot do

- **It is mortgages.** Trajectory *shapes* and cure behaviour transfer to consumer
  credit; absolute rates, cure timing, and exposure scale do not. Every rate quoted
  downstream names its source book.
- **No contact history.** Freddie Mac has no calls, no outreach, no channel. L3
  contactability and the conversation models are fed by the Home Credit / haessigDB /
  transcript assets, not this panel.
- **No borrower identity across loans.** One row is one loan, not one person.

## Verify

```bash
python -m ganymede.panel --build --verify
```

Gate checks: non-empty, all reporting periods parse to real dates, no period runs
backwards within a loan, static facts joined, and the delinquent class is present.
