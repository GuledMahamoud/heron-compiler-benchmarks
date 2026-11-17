"""Dense correctness checks for small outputs (up to 27 active qubits): exact operator comparison and
random entangled input states.  Larger outputs use frontier/random_check.py (matrix-product states)."""
from __future__ import annotations

import math
import time

STATE_MAX_QUBITS = 27
STATE_TRIALS = 6


def state_check(original, compiled, trials: int = STATE_TRIALS, rng_seed: int = 1234) -> dict:
    """Compare compiled and source as statevectors on random entangled inputs over the logical qubits
    (ancillas |0>), on the physical qubits the compiled circuit touches.  Worst infidelity reported."""
    import numpy as np
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector

    from harness.verify import reduced_pair
    red, ref, logical = reduced_pair(original, compiled)
    k = red.num_qubits
    if k > STATE_MAX_QUBITS:
        return {"status": "too_large", "active_qubits": k}
    rng = np.random.default_rng(rng_seed)
    worst, t0 = 0.0, time.perf_counter()
    for _ in range(trials):
        prep = QuantumCircuit(k)
        for layer in range(3):  # random rotations, then a ring of CZ: an entangled input with generic phases
            for q in logical:
                prep.u(*rng.uniform(0, 2 * math.pi, 3), q)
            order = list(rng.permutation(logical))
            if layer < 2 and len(order) > 1:
                for x, y in zip(order, order[1:] + order[:1]):
                    prep.cz(int(x), int(y))
        psi = Statevector.from_instruction(prep)
        a, b = psi.evolve(red), psi.evolve(ref)
        worst = max(worst, 1.0 - abs(np.vdot(a.data, b.data)) ** 2)
    return {"status": "states_agree" if worst <= 1e-6 else "states_differ", "active_qubits": k, "trials": trials,
            "worst_infidelity": float(worst), "wall": round(time.perf_counter() - t0, 1)}


def exact_check(original, compiled) -> dict | None:
    """harness.verify.exact_check (fixed there for logical qubits that end on an ancilla)."""
    from harness.verify import exact_check as _exact
    return _exact(original, compiled)
