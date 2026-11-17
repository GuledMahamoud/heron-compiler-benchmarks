"""Relative-phase Toffoli pairs: replace a compute/uncompute pair of Toffolis with two 3-CNOT
relative-phase Toffolis when it is safe to do so.

Background.  A relative-phase Toffoli R acts like a Toffoli up to a diagonal phase D (R = D * CCX) and
costs 3 CNOTs instead of 6.  It is a known construction (Barenco et al. 1995; Maslov, "Advantages of
using relative-phase Toffolis with an application to multiple control Toffoli optimization", PRA 93,
022311, 2016).  When a Toffoli is later undone by a second Toffoli on the same three qubits, both can be
replaced by R, because R is its own inverse here and the stray phases cancel, provided nothing in
between can tell the phase apart.

What this pass does.  It scans the circuit for a Toffoli and the next Toffoli with the same controls and
target.  Every instruction in between that touches those three qubits must be block-diagonal in the
computational basis of the qubits it shares with them (so it commutes with any diagonal phase on them);
the check is numerical, on the gate's own matrix, so it covers any gate of up to 5 qubits rather than a
fixed list.  Pairs that pass are rewritten; everything else is left alone.  The rewrite is exact: the
output is equivalent to the input, and a self-check at import time verifies the identity.

    from toffoli.relative_phase import relative_phase_rewrite, RelativePhaseToffoliPairs
    rewritten = relative_phase_rewrite(circuit)       # QuantumCircuit, or None when nothing to rewrite
    pm = PassManager([RelativePhaseToffoliPairs()])   # or as a Qiskit transpiler pass

On the benchmark circuits that contain such pairs it removed up to 41% of two-qubit gates after Qiskit
level 3 (see results/toffoli_pass/).  Circuits without pairs are unchanged.
"""
from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import CCXGate
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.quantum_info import Operator
from qiskit.transpiler.basepasses import TransformationPass

try:
    from qiskit.circuit.library import get_standard_gate_name_mapping
    _STD_NAMES = set(get_standard_gate_name_mapping().keys())
except Exception:  # noqa: BLE001
    _STD_NAMES = set()

MAX_CHECK_QUBITS = 5  # middle gates wider than this are treated as unsafe (no rewrite across them)


def _is_ccx(op) -> bool:
    return isinstance(op, CCXGate) and op.ctrl_state == 3 and len(op.params) == 0


def emit_relative_toffoli(qc: QuantumCircuit, a, b, t) -> None:
    """3-CNOT relative-phase Toffoli on controls a, b and target t."""
    qc.h(t); qc.t(t); qc.cx(b, t); qc.tdg(t); qc.cx(a, t)
    qc.t(t); qc.cx(b, t); qc.tdg(t); qc.h(t)


def _selfcheck() -> bool:
    """R = D * CCX with D diagonal, R is self-inverse, and a pair with a block-diagonal middle is exact."""
    r = QuantumCircuit(3); emit_relative_toffoli(r, 0, 1, 2)
    R, X = Operator(r).data, Operator(CCXGate()).data
    D = R @ X
    if np.max(np.abs(D - np.diag(np.diag(D)))) > 1e-9 or not np.allclose(R @ R, np.eye(8), atol=1e-9):
        return False
    qc = QuantumCircuit(5)
    qc.ccx(0, 1, 2); qc.cx(2, 3); qc.ccx(2, 4, 3); qc.t(0); qc.cz(1, 4); qc.rz(0.3, 2); qc.ccx(1, 0, 2)
    q2 = QuantumCircuit(5)
    emit_relative_toffoli(q2, 0, 1, 2); q2.cx(2, 3); q2.ccx(2, 4, 3); q2.t(0); q2.cz(1, 4); q2.rz(0.3, 2)
    emit_relative_toffoli(q2, 0, 1, 2)
    return Operator(qc).equiv(Operator(q2))


SELF_CHECK_OK = _selfcheck()
_BD_CACHE: dict = {}


def is_block_diagonal(op, local_qubits) -> bool:
    """True when `op` maps each computational-basis value of `local_qubits` (its own qubit indices) to
    itself, i.e. it commutes with any diagonal phase on those qubits."""
    key = None
    if op.name in _STD_NAMES:
        try:
            key = (op.name, op.num_qubits, tuple(float(p) for p in op.params), tuple(local_qubits))
        except Exception:  # noqa: BLE001 - symbolic parameters
            key = None
    if key is not None and key in _BD_CACHE:
        return _BD_CACHE[key]
    ok = False
    try:
        if op.num_qubits <= MAX_CHECK_QUBITS:
            U = Operator(op).data
            idx = np.arange(2 ** op.num_qubits)
            ok = True
            for k in local_qubits:
                z = 1 - 2 * ((idx >> k) & 1)
                if np.max(np.abs(U[z[:, None] != z[None, :]])) > 1e-9:
                    ok = False
                    break
    except Exception:  # noqa: BLE001 - no matrix available
        ok = False
    if key is not None:
        _BD_CACHE[key] = ok
    return ok


def flatten(circuit: QuantumCircuit) -> QuantumCircuit:
    """Decompose custom (non-standard) gates a few levels so Toffolis inside them become visible."""
    c = circuit
    for _ in range(3):
        names = {inst.operation.name for inst in c.data
                 if inst.operation.name not in _STD_NAMES and inst.operation.name not in ("barrier", "measure")
                 and getattr(inst.operation, "definition", None) is not None}
        if not names:
            break
        c = c.decompose(gates_to_decompose=list(names))
    return c


def relative_phase_rewrite(circuit: QuantumCircuit) -> QuantumCircuit | None:
    """The circuit with every safe compute/uncompute Toffoli pair replaced, or None if there are none."""
    if not SELF_CHECK_OK:
        return None
    idx = {q: i for i, q in enumerate(circuit.qubits)}
    insts = list(circuit.data)
    qs = [[idx[q] for q in inst.qubits] for inst in insts]
    isccx = [_is_ccx(inst.operation) and not inst.clbits for inst in insts]
    rep: dict[int, tuple[int, int, int]] = {}
    for i in range(len(insts)):
        if not isccx[i] or i in rep:
            continue
        a, b, t = qs[i]
        S = (a, b, t)
        for j in range(i + 1, len(insts)):
            q2 = qs[j]
            touched = [k for k, q in enumerate(q2) if q in S]
            if not touched or insts[j].operation.name == "barrier":
                continue
            if j in rep:  # an already-paired Toffoli in between: only safe if it does not act on our target
                if any(q2[k] == rep[j][2] for k in touched):
                    break
                continue
            if isccx[j] and q2[2] == t and {q2[0], q2[1]} == {a, b}:
                rep[i] = rep[j] = (a, b, t)
                break
            if insts[j].clbits or not is_block_diagonal(insts[j].operation, touched):
                break
    if not rep:
        return None
    out = circuit.copy_empty_like()
    Q = circuit.qubits
    for i, inst in enumerate(insts):
        if i in rep:
            a, b, t = rep[i]
            emit_relative_toffoli(out, Q[a], Q[b], Q[t])
        else:
            out.append(inst.operation, inst.qubits, inst.clbits)
    return out


class RelativePhaseToffoliPairs(TransformationPass):
    """Qiskit transpiler pass wrapping relative_phase_rewrite (run it before layout and routing)."""

    def run(self, dag):
        circ = flatten(dag_to_circuit(dag))
        new = relative_phase_rewrite(circ)
        return dag if new is None else circuit_to_dag(new)
