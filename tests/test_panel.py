"""Panel unit checks that don't need the full 1GB build — they run on tiny
synthetic Freddie-format bytes, so CI stays fast and offline."""

from ganymede.panel import _delinq_to_int, _parse_orig, _parse_perf


def test_delinq_mapping():
    assert _delinq_to_int("00") == 0
    assert _delinq_to_int("0") == 0
    assert _delinq_to_int("01") == 1
    assert _delinq_to_int("03") == 3
    assert _delinq_to_int("XX") is None
    assert _delinq_to_int("") is None
    assert _delinq_to_int("RA") == 99  # REO / terminal
    assert _delinq_to_int("R9") == 99


def _orig_bytes():
    # 31 pipe fields; only the indexed ones must be right.
    fields = ["716", "202603", "N", "205601", "", "30", "1", "P", "95", "32",
              "157000", "95", "5.875", "R", "N", "FRM", "IN", "SF", "474",
              "F26Q10000001", "P", "359", "1", "OTHER", "N", "", "", "N", "2", "N", "9999"]
    return ("|".join(fields) + "\n").encode()


def _perf_bytes():
    rows = [
        ["F26Q10000001", "202401", "175000.00", "00", "0", "180", "", "", "", "", "5.25", "0"],
        ["F26Q10000001", "202402", "174500.00", "01", "1", "179", "", "", "", "", "5.25", "0"],
    ]
    return ("\n".join("|".join(r) for r in rows) + "\n").encode()


def test_parse_orig_indexes():
    df = _parse_orig(_orig_bytes())
    row = df.to_dicts()[0]
    assert row["loan_id"] == "F26Q10000001"
    assert row["credit_score"] == 716
    assert row["orig_upb"] == 157000.0
    assert row["state"] == "IN"


def test_parse_perf_indexes_and_delinq():
    df = _parse_perf(_perf_bytes())
    rows = df.to_dicts()
    assert rows[0]["delinq"] == 0
    assert rows[1]["delinq"] == 1
    assert rows[0]["upb"] == 175000.0
