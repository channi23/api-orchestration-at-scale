"""Confidence metrics for any arm that outputs a probability for its chosen answer.

p[i] is the confidence the system attached to answer i, y[i] is 1 if that answer was correct.
All functions are pure and dependency-free so they can be unit-tested exactly.
"""
from __future__ import annotations

import math


def ece(p: list[float], y: list[int], bins: int = 10) -> float:
    """Expected Calibration Error with equal-width bins: sum_b |B_b|/n * |acc(B_b) - conf(B_b)|."""
    n = len(p)
    if n == 0:
        return float("nan")
    tot = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i in range(n) if (lo < p[i] <= hi) or (b == 0 and p[i] == 0.0)]
        if idx:
            acc = sum(y[i] for i in idx) / len(idx)
            conf = sum(p[i] for i in idx) / len(idx)
            tot += len(idx) / n * abs(acc - conf)
    return tot


def reliability(p: list[float], y: list[int], bins: int = 10) -> list[dict]:
    out = []
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i in range(len(p)) if (lo < p[i] <= hi) or (b == 0 and p[i] == 0.0)]
        out.append({"bin": [lo, hi], "n": len(idx),
                    "confidence": sum(p[i] for i in idx) / len(idx) if idx else None,
                    "accuracy": sum(y[i] for i in idx) / len(idx) if idx else None})
    return out


def brier(p: list[float], y: list[int]) -> float:
    """Binary Brier score of the 'chosen answer is correct' event (a strictly proper score)."""
    return sum((pi - yi) ** 2 for pi, yi in zip(p, y)) / len(p)


def brier_multiclass(probs: list[list[float]], gold: list[int]) -> float:
    """Mean over items of sum_k (p_k - 1[k = gold])^2. Range 0..2."""
    return sum(sum((pk - (1.0 if k == g else 0.0)) ** 2 for k, pk in enumerate(pr)) for pr, g in zip(probs, gold)) / len(gold)


def log_score(p_true: list[float], floor: float = 1e-4) -> float:
    """Mean negative log probability assigned to the true answer."""
    return -sum(math.log(max(pt, floor)) for pt in p_true) / len(p_true)


def risk_coverage(p: list[float], y: list[int]) -> list[tuple[float, float]]:
    """Selective prediction: answer only the most confident fraction. Returns (coverage, risk)."""
    order = sorted(range(len(p)), key=lambda i: -p[i])
    out, wrong = [], 0
    for k, i in enumerate(order, 1):
        wrong += 1 - y[i]
        out.append((k / len(p), wrong / k))
    return out


def aurc(p: list[float], y: list[int]) -> float:
    """Area under the risk-coverage curve (lower is better). Equals the error rate if confidence
    carries no information about correctness."""
    rc = risk_coverage(p, y)
    return sum(r for _, r in rc) / len(rc)


def coverage_at_risk(p: list[float], y: list[int], max_risk: float) -> float:
    """Largest coverage whose selective risk stays at or below ``max_risk``."""
    best = 0.0
    for cov, risk in risk_coverage(p, y):
        if risk <= max_risk:
            best = cov
    return best


def fit_temperature(logits: list[list[float]], gold: list[int], lo: float = 0.05, hi: float = 20.0) -> float:
    """One-parameter temperature scaling by golden-section search on the mean log loss.
    Fit on a calibration split only; never on the test split."""
    def nll(t: float) -> float:
        s = 0.0
        for z, g in zip(logits, gold):
            m = max(v / t for v in z)
            lse = m + math.log(sum(math.exp(v / t - m) for v in z))
            s += lse - z[g] / t
        return s / len(gold)
    gr = (math.sqrt(5) - 1) / 2
    a, b = math.log(lo), math.log(hi)
    c, d = b - gr * (b - a), a + gr * (b - a)
    for _ in range(60):
        if nll(math.exp(c)) < nll(math.exp(d)):
            b = d
        else:
            a = c
        c, d = b - gr * (b - a), a + gr * (b - a)
    return math.exp((a + b) / 2)
