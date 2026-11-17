"""One harness job: compile one benchmark with one seed, measure it, verify it, save it.

The function `compile_one` is what the worker processes run.  It returns a flat JSON-able record;
the sweep driver appends it to results/runs.jsonl.  Compiled circuits are saved as gzipped QPY
(layout included) so a later step can re-score the *same* compilations under a fidelity model instead
of recompiling.
"""
from __future__ import annotations

import gzip
import time
from pathlib import Path

from qiskit import qpy
from qiskit.transpiler import generate_preset_pass_manager

from . import benchmarks as B
from .target import DEFAULT_BASIS, DEFAULT_SPEC, make_target
from .verify import verify

_TARGET_CACHE: dict = {}


def target_for(spec: str = DEFAULT_SPEC, basis=DEFAULT_BASIS):
    key = (spec, tuple(basis))
    if key not in _TARGET_CACHE:
        _TARGET_CACHE[key] = make_target(spec, basis)
    return _TARGET_CACHE[key]


def compile_circuit(qc, seed: int, opt_level: int = 3, spec: str = DEFAULT_SPEC, basis=DEFAULT_BASIS):
    """Qiskit's preset pipeline, identical to transpile(..., optimization_level, seed_transpiler)."""
    pm = generate_preset_pass_manager(optimization_level=opt_level, target=target_for(spec, basis),
                                      seed_transpiler=seed)
    return pm.run(qc)


def layout_record(compiled) -> dict:
    lay = compiled.layout
    if lay is None:
        return {}
    return {
        # physical qubit holding logical qubit i at the start, and at the end (after routing swaps)
        "initial": [int(p) for p in lay.initial_index_layout(filter_ancillas=True)],
        "final": [int(p) for p in lay.final_index_layout(filter_ancillas=True)],
    }


def active_qubits(compiled) -> int:
    used = set()
    for inst in compiled.data:
        for q in inst.qubits:
            used.add(compiled.find_bit(q).index)
    return len(used)


def _err(e: BaseException) -> str:
    return f"{type(e).__name__}: {e}"[:300]


def compile_one(bench: B.Benchmark, seed: int, opt_level: int = 3, spec: str = DEFAULT_SPEC,
                basis=DEFAULT_BASIS, verify_timeout: float = 300.0, qpy_dir: Path | None = None,
                verify_threads: int = 1, preopt_dir: Path | None = None) -> dict:
    rec = {"kind": "run", "benchmark": bench.name, "seed": seed, "opt_level": opt_level}
    try:
        qc = B.prepare(B.load(bench))
    except Exception as e:
        rec.update(status="load_error", error=_err(e))
        return rec
    orig = B.stats(qc)

    to_compile = qc
    if preopt_dir is not None:
        # a pre-optimised version (pyzx / pytket) is mapped instead, but verified against the source
        pre = Path(preopt_dir) / f"{bench.name}.qpy.gz"
        if not pre.exists():
            rec.update(status="preopt_missing", error=f"no pre-optimised circuit at {pre.name}")
            return rec
        with gzip.open(pre, "rb") as f:
            to_compile = qpy.load(f)[0]
        rec["preopt"] = {"gates": to_compile.size(), "two_qubit": B.stats(to_compile)["two_qubit"]}

    t0 = time.perf_counter()
    try:
        out = compile_circuit(to_compile, seed, opt_level, spec, basis)
    except Exception as e:
        rec.update(status="transpile_error", error=_err(e), transpile_s=round(time.perf_counter() - t0, 3))
        return rec
    rec["transpile_s"] = round(time.perf_counter() - t0, 3)

    st = B.stats(out)
    rec.update(
        status="ok",
        two_qubit=st["two_qubit"], gates=st["gates"], depth=st["depth"], depth_2q=st["depth_2q"],
        ops=st["ops"], active_qubits=active_qubits(out), layout=layout_record(out),
    )

    rec["verify"] = verify(qc, out, timeout=verify_timeout, nonunitary=orig["nonunitary"],
                           threads=verify_threads)

    if qpy_dir is not None:
        d = Path(qpy_dir) / bench.name
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"seed_{seed:02d}.qpy.gz"
        with gzip.open(path, "wb") as f:
            qpy.dump(out, f)
        rec["qpy"] = str(path.relative_to(B.ROOT)) if path.is_relative_to(B.ROOT) else str(path)
    return rec
