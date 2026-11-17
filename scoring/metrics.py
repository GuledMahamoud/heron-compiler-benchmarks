"""Metrics for a compiled circuit on a device, and the cost used to rank compilations of one circuit.

metrics(): two-qubit gate count, two-qubit depth, scheduled duration (ns) and predicted damage (the
sum of gate-error, idle-decay and readout-error probabilities on the device's own calibration, from
harness.damage).  cost(..., "v3"): equal weights of the logs of those four, used to pick the best of
several seeds of the same compiler.  Lower is better for all of them.
"""
from __future__ import annotations

import math

OBJECTIVES: dict[str, dict[str, float]] = {
    "2q": {"two_qubit": 1.0},
    "v2": {"two_qubit": 1 / 3, "depth_2q": 1 / 3, "duration_ns": 1 / 3},
    "v3": {"two_qubit": 1 / 4, "depth_2q": 1 / 4, "duration_ns": 1 / 4, "damage": 1 / 4},
}

# added to each metric before taking ratios; 1 for counts and nanoseconds, none for damage
OFFSET: dict[str, float] = {"damage": 0.0}
DAMAGE_FLOOR = 1e-6  # keeps log() finite for an (impossible) zero-damage circuit

DESCRIPTIONS = {
    "2q": "two-qubit gate count",
    "v2": "two-qubit gate count, two-qubit depth and scheduled duration, equally weighted",
    "v3": "two-qubit gate count, two-qubit depth, scheduled duration and predicted damage, equally weighted",
}

_CAL: dict[int, object] = {}


def _calibration(target):
    key = id(target)
    if key not in _CAL:
        from harness.damage import from_target
        _CAL[key] = (target, from_target(target, "metrics"))  # keep target alive so id() stays unique
    return _CAL[key][1]


def two_qubit_ops(qc) -> int:
    return sum(1 for inst in qc.data if inst.operation.num_qubits == 2 and inst.operation.name != "barrier")


def metrics(qc, target) -> dict:
    """Every metric any objective uses, for a circuit already on `target`'s physical qubits."""
    from harness.damage import damage
    d = damage(qc, _calibration(target))
    return {
        "two_qubit": two_qubit_ops(qc),
        "depth_2q": qc.depth(filter_function=lambda i: i.operation.num_qubits == 2 and i.operation.name != "barrier"),
        "duration_ns": round(d["duration_us"] * 1e3, 1),
        "damage": max(DAMAGE_FLOOR, float(d["total"])),
    }


def _term(k: str, v: float) -> float:
    return math.log(v + OFFSET.get(k, 1.0))


def ratio(m: dict, base: dict, objective: str) -> float:
    """Per-circuit ratio against the baseline's metrics (lower is better, 1.0 = baseline)."""
    return math.exp(sum(w * (_term(k, m[k]) - _term(k, base[k])) for k, w in OBJECTIVES[objective].items()))


def cost(m: dict, objective: str) -> float:
    """A scalar for ranking compilations of the *same* circuit (e.g. picking the best of several seeds):
    lower is better and it orders compilations exactly as `ratio` does against any fixed baseline."""
    return sum(w * _term(k, m[k]) for k, w in OBJECTIVES[objective].items())
