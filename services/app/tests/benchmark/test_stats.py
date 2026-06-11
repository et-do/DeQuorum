from __future__ import annotations

from dequorum.benchmark.stats import ci_str, mean_ci, wilson_ci


def test_wilson_brackets_the_point_estimate() -> None:
    lo, hi = wilson_ci(75, 100)
    assert lo < 0.75 < hi
    assert 0.0 <= lo and hi <= 1.0


def test_ci_tightens_with_n() -> None:
    _, lo50, hi50 = mean_ci([1.0] * 38 + [0.0] * 12)  # ~0.75 @ N=50
    _, lo100, hi100 = mean_ci([1.0] * 75 + [0.0] * 25)  # ~0.75 @ N=100
    assert (hi100 - lo100) < (hi50 - lo50)


def test_boundaries_are_one_sided_not_zero_width() -> None:
    # all-zero (e.g. vote-gated false adoption) -> [0, small], not [0, 0]
    _, lo, hi = mean_ci([0.0] * 50)
    assert lo == 0.0 and 0.0 < hi < 0.1
    # all-one (e.g. routing accuracy) -> [near-1, 1], not [1, 1]
    _, lo, hi = mean_ci([1.0] * 50)
    assert hi == 1.0 and 0.9 < lo < 1.0


def test_ci_str_reports_mean_interval_and_n() -> None:
    s = ci_str([1.0] * 30 + [0.0] * 30)
    assert s.startswith("0.500 [")
    assert "(n=60)" in s


def test_empty_is_safe() -> None:
    assert ci_str([]) == "n/a"
    assert mean_ci([]) == (0.0, 0.0, 0.0)
