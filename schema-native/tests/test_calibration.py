import math

from sn import calibration as c


def test_perfectly_calibrated_bins_give_zero_ece():
    p = [0.75] * 4 + [0.25] * 4
    y = [1, 1, 1, 0] + [1, 0, 0, 0]
    assert c.ece(p, y) < 1e-12


def test_overconfidence_is_measured():
    assert abs(c.ece([1.0] * 10, [1] * 5 + [0] * 5) - 0.5) < 1e-12


def test_brier():
    assert c.brier([1.0, 0.0], [1, 0]) == 0.0
    assert c.brier([0.5, 0.5], [1, 0]) == 0.25
    assert c.brier_multiclass([[1.0, 0.0], [0.5, 0.5]], [0, 1]) == 0.25


def test_risk_coverage_orders_by_confidence():
    p, y = [0.9, 0.8, 0.2, 0.1], [1, 1, 0, 0]
    rc = c.risk_coverage(p, y)
    assert rc[1] == (0.5, 0.0) and rc[-1] == (1.0, 0.5)
    assert c.coverage_at_risk(p, y, 0.0) == 0.5
    assert c.aurc(p, y) < c.aurc(p, [0, 0, 1, 1])


def test_temperature_recovers_known_scale():
    import random
    rng = random.Random(0)
    logits, gold = [], []
    for _ in range(4000):
        z = [rng.gauss(0, 1) for _ in range(4)]
        probs = [math.exp(v) for v in z]
        s = sum(probs)
        r, acc, g = rng.random(), 0.0, 0
        for k, pk in enumerate(probs):
            acc += pk / s
            if r <= acc:
                g = k
                break
        logits.append([3.0 * v for v in z])       # over-confident by a factor of 3
        gold.append(g)
    assert abs(c.fit_temperature(logits, gold) - 3.0) < 0.3
