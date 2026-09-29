# Defect log

The reasoning behind each invariant: what broke, why it mattered, how it was
caught. The invariant table in the plan is the live constraint; this is the
history. A new defect gets an entry here, then an invariant with an
enforcement mechanism, never one without the other.

I1-I14 established in design review (v1 -> v3 of the plan). See the plan's
Design Invariants section for the current enforced form. This file grows as
new defects are found in the build.

## D15: forward labels crossed loan boundaries (found 2026-09-29)

**What broke.** `features.build_features` built its windows as
`pl.col("d").over("loan_id")` and then called `.shift()` and `.rolling_*()` on
that. Polars applies a method called after `.over()` to the whole broadcast
column, so the shift ran across the sorted frame. Each loan's last three rows
read the next loan's first months as their future (`y_worsen`, `y_selfcure`),
and its first rows took trailing features from the previous loan. The
forward-window filter also kept rows with only one or two future months,
because `max_horizontal` skips nulls.

**Why it mattered.** Every backtested and simulated headline sat on those
labels. After the fix: L1 AUC 0.62 to 0.66, L2 AUC 0.67 to 0.76, allocator edge
at 15% capacity +59.1% to +72.5%. The self-cure "regime shift" (0.60 to 0.72)
disappeared: the fixed rate moves from 0.59 to 0.52, inside the 0.10 alert band.

**How it was caught.** Code audit, then reproduced on a two-loan frame.

**Enforcement.** `tests/test_features.py` builds a two-loan panel where any
window that crosses the boundary shows a jump the first loan never made. It
fails on the old code and passes on the new.
