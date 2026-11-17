"""Random-input check for outputs too large for a formal proof (40+ qubits).

    nice -n 19 .venv/bin/python frontier/random_check.py frontier/results/<run> --only trotter-1

For each saved output in <run>/compiled/ and its source in <run>/sources/, on the physical qubits the
output uses (harness.verify.reduced_pair: the source placed at the output's initial layout, followed by
the routing permutation):

    random product state on the logical qubits (ancillas |0>)  ->  compiled output
    ->  inverse of the placed source  ->  inverse of the random state preparation

If the output is equivalent to the source, this returns exactly to |00...0>: the "return fidelity"
|<0|...|0>|^2 is 1.  A matrix-product-state simulator (qiskit-aer) handles 60+ qubits when the circuit
is not too entangling.  Its bond dimension is capped (--bond); a cap that bites lowers the fidelity of
correct and incorrect circuits alike, so every compiler's output is tested on the *same* random states
and the results are read side by side.  A negative control (the same program output with one two-qubit
gate removed) shows the test can see an error at all.

This is strong evidence, not a proof: a wrong circuit could, in principle, agree on every state tried.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def return_fidelity(red, ref, logical, seed: int, bond: int) -> tuple[float, float]:
    """(|<0|P^-1 R^-1 C P|0>|^2, seconds) for compiled C, reference R, random product preparation P."""
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator
    rng = random.Random(seed)
    k = red.num_qubits
    prep = QuantumCircuit(k)
    for q in logical:
        prep.u(math.acos(1 - 2 * rng.random()), rng.uniform(-math.pi, math.pi), rng.uniform(-math.pi, math.pi), q)
    circ = QuantumCircuit(k)
    circ.compose(prep, inplace=True)
    circ.compose(red, inplace=True)
    circ.compose(ref.inverse(), inplace=True)
    circ.compose(prep.inverse(), inplace=True)
    circ = transpile(circ, basis_gates=["u", "cx", "cz", "swap"], optimization_level=0)
    circ.save_amplitudes([0])
    sim = AerSimulator(method="matrix_product_state", matrix_product_state_max_bond_dimension=bond)
    t0 = time.perf_counter()
    amp = sim.run(circ, shots=1).result().data(0)["amplitudes"][0]
    return float(abs(amp) ** 2), time.perf_counter() - t0


def drop_one_2q(circ, seed: int):
    """Copy of `circ` with one two-qubit gate (chosen at random, middle half) removed: a negative control."""
    out = circ.copy_empty_like()
    idx = [i for i, inst in enumerate(circ.data) if inst.operation.num_qubits == 2]
    rng = random.Random(seed)
    drop = rng.choice(idx[len(idx) // 4: 3 * len(idx) // 4] or idx)
    for i, inst in enumerate(circ.data):
        if i != drop:
            out.append(inst.operation, inst.qubits, inst.clbits)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run", type=Path)
    ap.add_argument("--only", action="append", default=None,
                    help="only outputs whose file name contains this text; repeat for several")
    ap.add_argument("--trials", type=int, default=6)
    ap.add_argument("--bond", type=int, default=256, help="MPS bond-dimension cap (memory grows as its square)")
    ap.add_argument("--no-control", action="store_true", help="skip the deliberately broken negative control")
    a = ap.parse_args()
    try:
        os.nice(19)
    except OSError:
        pass
    from qiskit import qpy
    from harness.verify import reduced_pair

    run = a.run if a.run.is_absolute() else ROOT / a.run
    outs = sorted((run / "compiled").glob("*.qpy.gz"))
    if a.only:
        outs = [p for p in outs if any(o in p.name for o in a.only)]
    by_circuit: dict[str, list[Path]] = {}
    for p in outs:
        by_circuit.setdefault(p.name[:-len(".qpy.gz")].partition("__")[0], []).append(p)
    results = []
    for circuit, paths in sorted(by_circuit.items()):
        with open(run / "sources" / f"{circuit}.qpy", "rb") as f:
            src = qpy.load(f)[0]
        cases = []
        for p in sorted(paths):
            with gzip.open(p, "rb") as f:
                cases.append((p.name[:-len(".qpy.gz")].partition("__")[2], qpy.load(f)[0]))
        if not a.no_control:
            g = next((c for c in cases if c[0].startswith("g0")), cases[0])
            broken = g[1].copy()
            broken.data = drop_one_2q(g[1], 0).data
            cases.append((f"{g[0]} BROKEN (control)", broken))
        print(f"{circuit}: {len(cases)} outputs x {a.trials} random states, bond cap {a.bond}", flush=True)
        for label, out in cases:
            red, ref, logical = reduced_pair(src, out)
            fids, secs = [], 0.0
            for t in range(a.trials):
                fid, dt = return_fidelity(red, ref, logical, seed=1000 + t, bond=a.bond)
                fids.append(fid); secs += dt
                print(f"  {label:<28} state {t + 1}/{a.trials}: return fidelity {fid:.6f}  ({dt:.0f} s)", flush=True)
            rec = {"circuit": circuit, "compiler": label, "qubits": red.num_qubits, "trials": a.trials, "bond": a.bond,
                   "min_fidelity": min(fids), "mean_fidelity": sum(fids) / len(fids), "fidelities": fids,
                   "minutes": round(secs / 60, 1)}
            results.append(rec)
            (run / "random_check.json").write_text(json.dumps(results, indent=1))
            L = [f"# Random-input check — {datetime.now():%Y-%m-%d %H:%M}", "",
                 "Return fidelity on random product inputs (1.0 = output matches the source on that input). "
                 f"MPS simulator, bond cap {a.bond}; compare rows of the same circuit side by side. "
                 "The BROKEN row is a negative control with one two-qubit gate removed: it should score clearly lower.", "",
                 "| circuit | compiler | qubits | states | min fidelity | mean fidelity | minutes |", "|---|---|---:|---:|---:|---:|---:|"]
            L += [f"| {r['circuit']} | {r['compiler']} | {r['qubits']} | {r['trials']} | {r['min_fidelity']:.6f} | "
                  f"{r['mean_fidelity']:.6f} | {r['minutes']} |" for r in results]
            (run / "RANDOM_CHECK.md").write_text("\n".join(L) + "\n")
    print(f"done: {(run / 'RANDOM_CHECK.md').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
