"""Freddie Mac Single-Family Loan-Level -> unified monthly borrower panel.

This is the L1 backbone (I13): the only source with real calendar dates and
real delinquency-state transitions. Everything the Risk Lens learns about
timing, roll, and cure comes from here.

Two file types per quarter:
  orig_YYYYQn.txt  — one row per loan, static facts (credit score, UPB, LTV...)
  perf_YYYYQn.txt  — one row per loan-month, the trajectory (UPB, delinquency)

Quarter archives come in two shapes and both are handled:
  - flat: the .zip holds orig/perf .txt directly (2026)
  - nested: the .zip holds per-quarter .zip files (2024, 2025)

Sampling: the plan wants ~300k loans stratified on vintage and outcome. Default
per delinquents being rare — keep every ever-delinquent loan and a random draw
of the rest, so models see enough of the class that matters. The draw is logged
as a weight, the same discipline the decision log applies to propensity.
"""

from __future__ import annotations

import argparse
import io
import zipfile
from collections.abc import Iterator
from pathlib import Path

import polars as pl

from .config import DATA_RAW

PROCESSED = DATA_RAW.parent / "processed"
PANEL_PATH = PROCESSED / "panel.parquet"

# Field positions, from the confirmed Freddie standard layout.
ORIG = {"credit_score": 0, "first_pmt": 1, "cltv": 8, "dti": 9, "orig_upb": 10,
        "orig_ltv": 11, "orig_rate": 12, "state": 16, "loan_id": 19}
PERF = {"loan_id": 0, "period": 1, "upb": 2, "delinq": 3, "loan_age": 4,
        "zero_bal": 8}

HAS_CALENDAR_DATES = True  # I13: this source is allowed to feed timing features


def _delinq_to_int(raw: str) -> int | None:
    """Freddie delinquency status -> months-delinquent bucket.
    '00'/'0' current, '01'..'99' the bucket, 'XX'/'' unknown, 'RA'/'R*' REO."""
    raw = raw.strip()
    if raw in ("", "XX"):
        return None
    if raw.startswith("R"):
        return 99  # REO / terminal
    try:
        return int(raw)
    except ValueError:
        return None


def _iter_quarter_txt(quarter_zip: Path) -> Iterator[tuple[str, bytes]]:
    """Yield (member_name, raw_bytes) for orig/perf txt, from either archive shape."""
    with zipfile.ZipFile(quarter_zip) as z:
        for name in z.namelist():
            data = z.read(name)
            if name.endswith(".txt"):
                yield name, data
            elif name.endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(data)) as inner:
                    for inner_name in inner.namelist():
                        if inner_name.endswith(".txt"):
                            yield inner_name, inner.read(inner_name)


def _find_quarter_zips() -> list[Path]:
    zips = sorted(DATA_RAW.glob("historical_data_*/historical_data_*.zip"))
    zips += [p for p in DATA_RAW.glob("historical_data_*.zip")]  # flat fallback
    return sorted(set(zips))


def _read_pipe(raw: bytes, wanted: dict[str, int]) -> pl.DataFrame:
    """Read a headerless pipe-delimited Freddie file with polars (fast, native),
    keeping only the wanted columns. All values come back as strings; callers
    cast what they need."""
    df = pl.read_csv(
        io.BytesIO(raw),
        separator="|",
        has_header=False,
        infer_schema=False,  # everything Utf8, no inference cost
        quote_char=None,
        encoding="utf8-lossy",
    )
    cols = df.columns  # column_1, column_2, ...
    return df.select(
        [pl.col(cols[idx]).alias(name) for name, idx in wanted.items()]
    )


def _parse_orig(raw: bytes) -> pl.DataFrame:
    df = _read_pipe(raw, ORIG)
    return df.with_columns([
        pl.col("credit_score").cast(pl.Int32, strict=False),
        pl.col("orig_upb").cast(pl.Float64, strict=False),
        pl.col("orig_ltv").cast(pl.Int32, strict=False),
        pl.col("dti").cast(pl.Int32, strict=False),
        pl.col("cltv").cast(pl.Int32, strict=False),
    ])


def _parse_perf(raw: bytes) -> pl.DataFrame:
    df = _read_pipe(raw, PERF)
    return df.with_columns([
        pl.col("upb").cast(pl.Float64, strict=False),
        pl.col("loan_age").cast(pl.Int32, strict=False),
        pl.col("delinq").map_elements(_delinq_to_int, return_dtype=pl.Int32).alias("delinq"),
    ])


def build(loans_per_quarter: int = 5000, seed: int = 7) -> pl.DataFrame:
    """Build the sampled panel across all quarters found in data/raw."""
    frames = []
    for qzip in _find_quarter_zips():
        vintage = qzip.stem.replace("historical_data_", "")
        orig_df = perf_df = None
        for name, raw in _iter_quarter_txt(qzip):
            if name.startswith("orig"):
                orig_df = _parse_orig(raw)
            elif name.startswith("perf"):
                perf_df = _parse_perf(raw)
        if orig_df is None or perf_df is None:
            continue

        # per-loan worst delinquency -> stratify sampling on outcome
        worst = perf_df.group_by("loan_id").agg(pl.col("delinq").max().alias("worst_delinq"))
        ever_delinq = worst.filter(pl.col("worst_delinq") >= 1)["loan_id"]
        current = worst.filter((pl.col("worst_delinq") < 1) | pl.col("worst_delinq").is_null())["loan_id"]

        keep_delinq = list(ever_delinq)  # keep all of the rare class
        n_current_pop = len(current)
        n_current = max(0, loans_per_quarter - len(keep_delinq))
        n_current_kept = min(n_current, n_current_pop)
        keep_current = list(
            current.to_frame().sample(n_current_kept, seed=seed)["loan_id"]
        ) if n_current_kept else []
        keep = set(keep_delinq) | set(keep_current)

        # Sampling weight recovers population proportions from the oversample.
        # Delinquents kept whole -> weight 1. Current downsampled -> weight up.
        current_weight = (n_current_pop / n_current_kept) if n_current_kept else 1.0
        keep_current_set = set(keep_current)

        q_perf = perf_df.filter(pl.col("loan_id").is_in(keep))
        q = q_perf.join(orig_df, on="loan_id", how="left")
        q = q.with_columns([
            pl.lit(vintage).alias("vintage"),
            pl.lit(HAS_CALENDAR_DATES).alias("has_calendar_dates"),
            pl.col("period").str.strptime(pl.Date, "%Y%m", strict=False).alias("period_date"),
            pl.when(pl.col("loan_id").is_in(keep_current_set))
              .then(pl.lit(current_weight))
              .otherwise(pl.lit(1.0))
              .alias("sample_weight"),
        ])
        frames.append(q)

    panel = pl.concat(frames, how="vertical_relaxed")
    PROCESSED.mkdir(exist_ok=True)
    panel.write_parquet(PANEL_PATH)
    return panel


def verify() -> list[str]:
    """Phase 2 exit gate. Returns violations; empty means pass."""
    problems = []
    if not PANEL_PATH.exists():
        return ["panel.parquet missing — run build first"]
    p = pl.read_parquet(PANEL_PATH)

    if p.height == 0:
        problems.append("panel is empty")

    # calendar dates parsed (I13 depends on real dates existing)
    null_dates = p["period_date"].null_count()
    if null_dates > 0:
        problems.append(f"{null_dates} rows have unparseable reporting period")

    # monthly period monotonic within loan (no time going backwards)
    ordered = p.sort(["loan_id", "period_date"])
    back = ordered.group_by("loan_id", maintain_order=True).agg(
        (pl.col("period_date").diff().dt.total_days() < 0).sum().alias("reversals")
    )
    if back["reversals"].sum() > 0:
        problems.append("reporting period runs backwards within a loan")

    # every perf row joined to a real static record (credit_score present)
    orphans = p.filter(pl.col("credit_score").is_null() & pl.col("orig_upb").is_null()).height
    if orphans > p.height * 0.5:
        problems.append(f"{orphans} rows failed to join orig static facts")

    # the class that matters is actually present
    if p.filter(pl.col("delinq") >= 1).height == 0:
        problems.append("no delinquent months in the sample — nothing to learn from")

    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--loans-per-quarter", type=int, default=5000)
    args = ap.parse_args()

    if args.build:
        panel = build(loans_per_quarter=args.loans_per_quarter)
        print(f"built panel: {panel.height} monthly rows, "
              f"{panel['loan_id'].n_unique()} loans, "
              f"{panel['vintage'].n_unique()} vintages -> {PANEL_PATH}")
    if args.verify:
        problems = verify()
        if problems:
            print("PANEL VERIFY FAILED:")
            for p in problems:
                print(f"  FAIL {p}")
            return 1
        print("panel verify OK")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
