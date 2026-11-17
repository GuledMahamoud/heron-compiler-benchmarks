"""Equivalence checking with mqt.qcec, with a hard wall-clock guard.

Every compiled circuit is checked against the circuit it was compiled from.  Qiskit records the
layout on the compiled circuit (which logical qubit went to which physical qubit, and the final
permutation that routing left behind); qcec reads that layout, so a compiled circuit on 57 physical
qubits is compared directly with its n-qubit original, the untouched qubits being idle ancillas.

Why a child process: qcec's own `timeout` is only honoured between decision-diagram operations.  On
routed circuits whose SWAP networks reorder a compact unitary (an 18-qubit QFT was enough) one
operation can run for many minutes, and some configurations abort outright.  Each check therefore
runs in `python -m harness.verify`, a child fed over a pipe and killed when the limit passes.
Costs ~1-2 s of interpreter start-up per check, buys a harness that always finishes.

Two-stage policy, measured on this benchmark set (see README "Verification"):

    1. formal   -- the alternating checker alone.  It is the checker built for compilation-flow
                   verification and the only one that ever succeeded where the others failed.
                   -> equivalent | equivalent_up_to_global_phase | not_equivalent
    2. fallback -- if stage 1 timed out or gave no information: 16 random computational-basis
                   simulations.  Cheap everywhere (random stabilizer / single-qubit-basis stimuli
                   were not: 10-100x slower and one configuration crashed qcec).  Catches any error
                   that changes output amplitudes; can miss a pure phase error.  The per-simulation
                   fidelity threshold is 1e-6, not qcec's 1e-8: on qft_n18 (2,600 gates, angles down
                   to pi/2^17) rounding drift in the decision diagrams produced false refutations at
                   1e-8, while a circuit with one gate deleted is still refuted on the first run.
                   -> probably_equivalent | probably_not_equivalent | not_equivalent

    plus timeout | no_information | error when neither could decide.

Sources with mid-circuit measurement, reset or classical control are checked with qcec's
deferred-measurement transform and partial equivalence (discarded qubits ignored).  A refutation on
such a source is reported as `not_equivalent_unconfirmed`: on square_root_n18 the same machinery
accepts the unrouted translation and rejects every routed one, which is a lead for a later step to
reproduce independently, not a verdict.

"Equivalent" everywhere means process infidelity ≤ 1e-6 (EQUIVALENCE_TOLERANCE): Qiskit's gate synthesis
leaves deviations around 1e-7 (hhl_n7 seed 24 on Torino), a thousand times below any hardware error,
and qcec's default trace threshold of 1e-8 refuses them.  Refutations get two second opinions: an
exact dense-operator comparison when the circuit touches ≤ 12 physical qubits, and qcec again with
its layout handling bypassed (source at the initial layout + the routing permutation as SWAPs).

`passed` is true only for a formal proof; `probable` is true for `probably_equivalent`.  The report
keeps the two apart: the headline counts proofs, the table shows where only the randomised check held.
"""
from __future__ import annotations

import os
import pickle
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PASS = {"equivalent", "equivalent_up_to_global_phase", "equivalent_up_to_phase"}
PROBABLE = {"probably_equivalent"}
REFUTED = {"not_equivalent", "probably_not_equivalent"}

EQUIVALENCE_TOLERANCE = 1e-6  # process infidelity accepted as "equivalent": Qiskit's synthesis numerics leave ~1e-7
_FORMAL = dict(run_alternating_checker=True, run_construction_checker=False, run_simulation_checker=False,
               run_zx_checker=False, trace_threshold=EQUIVALENCE_TOLERANCE)
FALLBACK_FIDELITY_THRESHOLD = 1e-6  # qcec default 1e-8 trips on decision-diagram rounding drift (qft_n18)
_FALLBACK = dict(run_alternating_checker=False, run_construction_checker=False, run_simulation_checker=True,
                 run_zx_checker=False, max_sims=16, fidelity_threshold=FALLBACK_FIDELITY_THRESHOLD)


def version() -> str:
    from mqt import qcec
    return getattr(qcec, "__version__", "unknown")


def _criterion_name(criterion) -> str:
    return str(criterion).split(".")[-1]  # "EquivalenceCriterion.equivalent" -> "equivalent"


# ----------------------------------------------------------------------------- child side
def check(original, compiled, **kwargs) -> dict:
    """One qcec.verify call, in this process.  Used by the child; callable directly for debugging."""
    from mqt import qcec
    t0 = time.perf_counter()
    res = qcec.verify(original, compiled, **kwargs)
    return {"status": _criterion_name(res.equivalence), "check_time": round(float(res.check_time), 3),
            "preprocessing_time": round(float(res.preprocessing_time), 3),
            "simulations": int(res.performed_simulations), "wall": round(time.perf_counter() - t0, 3)}


def _quiet_fatal_signals() -> None:
    """qcec sometimes aborts (std::terminate) or segfaults.  Route those signals to libc's _exit so the
    child just exits with the signal number instead of crashing: the parent records 'aborted', and
    macOS does not pop a 'Python quit unexpectedly' dialog for an orderly exit."""
    import ctypes
    import signal
    try:
        libc = ctypes.CDLL(None)
        libc.signal.argtypes = [ctypes.c_int, ctypes.c_void_p]
        libc.signal.restype = ctypes.c_void_p
        exit_ptr = ctypes.cast(libc._exit, ctypes.c_void_p).value
        for sig in (signal.SIGABRT, signal.SIGSEGV, signal.SIGBUS, signal.SIGILL, signal.SIGFPE):
            libc.signal(int(sig), exit_ptr)
    except Exception:  # noqa: BLE001 - best effort; without it we only lose the quiet exit
        pass


def _child_main() -> None:
    _quiet_fatal_signals()
    src, out, kwargs = pickle.loads(sys.stdin.buffer.read())
    try:
        rec = check(src, out, **kwargs)
    except BaseException as e:  # noqa: BLE001 - report everything, the parent decides
        rec = {"status": "error", "error": f"{type(e).__name__}: {e}"[:300]}
    sys.stdout.buffer.write(pickle.dumps(rec))
    sys.stdout.buffer.flush()


# ----------------------------------------------------------------------------- parent side
def explicit_reference(original, compiled):
    """(reference, compiled-without-layout): the source placed at the initial layout followed by the
    routing permutation as explicit SWAPs, so equivalence can be checked with qcec's layout handling
    bypassed.  Used as a second opinion on refutations: on hhl_n7 (Torino, seed 24) qcec's layout
    import refuted a compilation that an exact statevector comparison shows is correct."""
    from qiskit import QuantumCircuit
    from qiskit.synthesis import synth_permutation_basic
    lay = compiled.layout
    if lay is None:
        return None, None
    init = lay.initial_index_layout(filter_ancillas=True)
    perm = lay.routing_permutation()
    ref = QuantumCircuit(compiled.num_qubits)
    ref.compose(original, qubits=init, inplace=True)
    pattern = [0] * len(perm)
    for i, j in enumerate(perm):
        pattern[j] = i
    ref.compose(synth_permutation_basic(pattern), inplace=True)
    nolayout = compiled.copy()
    nolayout._layout = None
    return ref, nolayout


EXACT_MAX_QUBITS = 12


def reduced_pair(original, compiled):
    """(compiled restricted to the physical qubits it uses, reference on the same qubits, logical positions).

    The reference is the source placed at the initial layout followed by the routing permutation.  When
    routing leaves a logical qubit on what started as an ancilla, the sets of initial and final sites
    differ; the leftover sites (ancillas, which start in |0>) are paired among themselves so that the
    permutation is a real one.  Before this was done, hhl_n7 compiled by one of the compilers under test was
    reported as not equivalent although it is (process infidelity 1.6e-11 on the logical space)."""
    from qiskit import QuantumCircuit
    from qiskit.synthesis import synth_permutation_basic
    lay = compiled.layout
    init = lay.initial_index_layout(filter_ancillas=True)
    fin = lay.final_index_layout(filter_ancillas=True)
    touched = {compiled.find_bit(q).index for inst in compiled.data for q in inst.qubits}
    active = sorted(touched | set(init) | set(fin))
    k = len(active)
    pos = {p: i for i, p in enumerate(active)}
    red = QuantumCircuit(k)
    for inst in compiled.data:
        if inst.operation.name == "barrier":
            continue
        red.append(inst.operation, [pos[compiled.find_bit(q).index] for q in inst.qubits])
    ref = QuantumCircuit(k)
    ref.compose(original, qubits=[pos[p] for p in init], inplace=True)
    pattern = [None] * k
    for l in range(original.num_qubits):
        pattern[pos[fin[l]]] = pos[init[l]]
    starts = {pos[p] for p in init}
    spare = [i for i in range(k) if i not in starts]
    for i in range(k):
        if pattern[i] is None:
            pattern[i] = spare.pop(0)
    ref.compose(synth_permutation_basic(pattern), inplace=True)
    return red, ref, [pos[p] for p in init]


def exact_check(original, compiled) -> dict | None:
    """Definitive check for small circuits: the compiled circuit and the reference (see reduced_pair) as
    dense operators on the physical qubits the circuit uses (k <= EXACT_MAX_QUBITS), compared on every
    input whose ancillas are |0> -- the only inputs a compiled circuit is required to get right.  Process
    infidelity on that subspace, phase-free.  Returns None when too big."""
    if compiled.layout is None:
        return None
    t0 = time.perf_counter()
    try:
        red, ref, logical = reduced_pair(original, compiled)
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": f"exact check: {type(e).__name__}: {e}"[:200]}
    k = red.num_qubits
    if k > EXACT_MAX_QUBITS:
        return None
    try:
        import numpy as np
        from qiskit.quantum_info import Operator
        A, R = Operator(red).data, Operator(ref).data
        anc = sum(1 << q for q in range(k) if q not in logical)
        cols = [c for c in range(2 ** k) if not c & anc]
        infidelity = 1.0 - abs(np.trace(A[:, cols].conj().T @ R[:, cols]) / len(cols)) ** 2
    except Exception as e:  # noqa: BLE001 - non-unitary ops (reset, measure) have no operator
        return {"status": "error", "error": f"exact check: {type(e).__name__}: {e}"[:200]}
    same = infidelity <= EQUIVALENCE_TOLERANCE
    return {"status": "equivalent_up_to_global_phase" if same else "not_equivalent", "active_qubits": k,
            "process_infidelity": float(infidelity), "wall": round(time.perf_counter() - t0, 3)}


def _guarded(payload: bytes, limit: float) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    p = subprocess.Popen([sys.executable, "-m", "harness.verify"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, cwd=str(ROOT), env=env)
    try:
        out, err = p.communicate(payload, timeout=limit)
    except subprocess.TimeoutExpired:
        p.kill()
        p.communicate()
        return {"status": "timeout"}
    if p.returncode != 0 or not out:
        import signal
        tail = err.decode(errors="replace").strip().splitlines()[-1:] if err else []
        code = p.returncode
        name = signal.Signals(abs(code)).name if code and abs(code) in signal.Signals._value2member_map_ else None
        what = f"verifier aborted ({name})" if name else f"verifier process exit {code}"
        return {"status": "error", "error": f"{what}: {' '.join(tail)}".strip(": ")[:300]}
    try:
        return pickle.loads(out)
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": f"unreadable verifier output: {e}"[:300]}


def verify(original, compiled, timeout: float = 60.0, nonunitary: bool = False, threads: int = 1,
           fallback: bool = True) -> dict:
    """Check `compiled` against `original`.  Never raises; failures come back as status strings."""
    t0 = time.perf_counter()
    common: dict = {"timeout": float(timeout), "parallel": threads > 1, "nthreads": max(1, threads)}
    if nonunitary:
        common.update(transform_dynamic_circuit=True, check_partial_equivalence=True)

    rec = _guarded(pickle.dumps((original, compiled, {**common, **_FORMAL})), timeout + 10.0)
    rec.update(stage="formal", checker="alternating")
    status = rec["status"]
    if fallback and status in ("timeout", "no_information", "error"):
        fb = _guarded(pickle.dumps((original, compiled, {**common, **_FALLBACK})), timeout + 10.0)
        if fb["status"] in PROBABLE | REFUTED:
            rec = {**fb, "stage": "fallback", "checker": "simulation", "formal_status": status,
                   "fidelity_threshold": FALLBACK_FIDELITY_THRESHOLD,
                   **({"formal_error": rec["error"]} if "error" in rec else {})}
            status = fb["status"]
        else:
            rec["fallback_status"] = fb["status"]
            if "error" in fb:
                rec["fallback_error"] = fb["error"]
    if status in REFUTED and not nonunitary:
        # second opinion 1: exact dense-operator comparison when the circuit is small enough.  qcec 3.9's
        # alternating checker refuted hhl_n7 seed 24 (Torino) under every configuration while the
        # 128x128 operators are identical up to phase; this is the definitive answer for such cases.
        ex = exact_check(original, compiled)
        if ex and ex["status"] in PASS:
            rec = {**ex, "stage": "formal", "checker": "exact_operator", "qcec_status": status}
            status = ex["status"]
        elif ex and ex["status"] in REFUTED:
            rec["exact_check"] = ex["status"]
    if status in REFUTED:
        # second opinion 2: qcec with its layout handling bypassed; a proof here overrides the refutation
        ref, nolayout = explicit_reference(original, compiled)
        if ref is not None:
            so = _guarded(pickle.dumps((ref, nolayout, {**common, **_FORMAL})), timeout + 10.0)
            rec["second_opinion"] = so.get("status")
            if so.get("status") in PASS:
                rec = {**so, "stage": "formal", "checker": "alternating", "via": "explicit_permutation",
                       "layout_import_status": status}
                status = so["status"]
    if nonunitary and status in REFUTED:
        status = "not_equivalent_unconfirmed"
    rec["status"] = status
    rec["passed"] = status in PASS
    rec["probable"] = status in PROBABLE
    rec["seconds"] = round(time.perf_counter() - t0, 3)
    return rec


if __name__ == "__main__":
    _child_main()
