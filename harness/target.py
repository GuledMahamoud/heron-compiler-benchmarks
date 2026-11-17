"""The compilation target: IBM-style heavy-hex lattice, Heron-style native gates.

`CouplingMap.from_heavy_hex(5)` is the distance-5 heavy-hex lattice (57 qubits), the same
topology family as IBM's Eagle/Heron processors but with uniform, nameless qubits.  a later step
replaces this with a real backend's Target (which carries per-gate error rates) -- the harness only
ever sees a Target, so that swap is a one-line change.
"""
from __future__ import annotations

from qiskit.circuit import IfElseOp
from qiskit.transpiler import CouplingMap, Target

DEFAULT_DISTANCE = 5
DEFAULT_BASIS = ("rz", "sx", "x", "cz")  # Heron-style; use ("rz","sx","x","ecr") for Eagle


def heavy_hex_coupling_map(distance: int = DEFAULT_DISTANCE) -> CouplingMap:
    return CouplingMap.from_heavy_hex(distance, bidirectional=True)


def heavy_hex_target(distance: int = DEFAULT_DISTANCE, basis=DEFAULT_BASIS) -> Target:
    cm = heavy_hex_coupling_map(distance)
    target = Target.from_configuration(
        basis_gates=list(basis) + ["measure", "reset"],
        num_qubits=cm.size(),
        coupling_map=cm,
    )
    # A handful of QASMBench circuits use classical conditions (`if (c==1) x q;`); let the
    # target accept them so they compile, and let the verifier say whether it can check them.
    target.add_instruction(IfElseOp, name="if_else")
    return target


def describe(distance: int = DEFAULT_DISTANCE, basis=DEFAULT_BASIS) -> dict:
    cm = heavy_hex_coupling_map(distance)
    return {
        "coupling_map": f"heavy_hex(distance={distance})",
        "num_qubits": cm.size(),
        "num_edges": len(cm.get_edges()) // 2,
        "basis_gates": list(basis),
    }


# ----------------------------------------------------------------------------- target specs
# "heavy_hex:5"      -> the abstract 57-qubit lattice above (uniform, nameless qubits)
# "fake:FakeTorino"  -> a real device Target from qiskit-ibm-runtime's fake provider, with the
#                       calibration snapshot's per-gate errors and durations attached
DEFAULT_SPEC = f"heavy_hex:{DEFAULT_DISTANCE}"


def make_target(spec: str = DEFAULT_SPEC, basis=DEFAULT_BASIS) -> Target:
    kind, _, arg = spec.partition(":")
    if kind == "heavy_hex":
        return heavy_hex_target(int(arg or DEFAULT_DISTANCE), basis)
    if kind == "fake":
        from qiskit_ibm_runtime import fake_provider as fp
        name, _, opt = arg.partition("@")
        target = getattr(fp, name)().target
        if opt.startswith("prune="):
            target = prune_couplers(target, float(opt[6:]))
        return target
    if kind == "ibm":   # a real machine's live Target (needs saved IBM Quantum credentials)
        from qiskit_ibm_runtime import QiskitRuntimeService
        return QiskitRuntimeService().backend(arg).target
    raise ValueError(f"unknown target spec {spec!r}")


def prune_couplers(target: Target, max_error: float) -> Target:
    """Copy of a device Target without two-qubit gates on couplers whose error exceeds `max_error`,
    keeping any coupler whose removal would disconnect the graph.  Routing on the pruned target is
    forced around the bad couplers: an earlier test's "cross the bad link" move at the compiler level."""
    import rustworkx as rx
    two_q = [op for op in target.operation_names if target.operation_from_name(op).num_qubits == 2]
    g = target.build_coupling_map().graph.to_undirected(multigraph=False)
    bad = sorted({tuple(sorted(q)) for op in two_q for q, p in target[op].items() if p is not None and p.error is not None and p.error > max_error},
                 key=lambda e: -max(target[op][q].error for op in two_q for q in (e, e[::-1]) if q in target[op] and target[op][q] is not None and target[op][q].error is not None))
    removed = set()
    for e in bad:
        g2 = g.copy(); g2.remove_edge(*e)
        if rx.is_connected(g2):
            g = g2; removed.add(e)
    new = Target(num_qubits=target.num_qubits, dt=target.dt, qubit_properties=target.qubit_properties)
    for op in target.operation_names:
        props = target[op]
        if op in two_q:
            props = {q: p for q, p in props.items() if tuple(sorted(q)) not in removed}
        if props is None or set(props) == {None}:   # global instruction added by class (if_else, ...)
            new.add_instruction(target.operation_from_name(op), name=op)
        else:
            new.add_instruction(target.operation_from_name(op), dict(props), name=op)
    PRUNE_INFO[id(new)] = {"max_error": max_error, "removed": sorted(removed)}
    return new


PRUNE_INFO: dict = {}   # Target is a Rust object and takes no attributes; keyed by id(target)


def describe_spec(spec: str = DEFAULT_SPEC, basis=DEFAULT_BASIS) -> dict:
    kind, _, arg = spec.partition(":")
    if kind == "heavy_hex":
        return {"spec": spec, **describe(int(arg or DEFAULT_DISTANCE), basis)}
    tg = make_target(spec)
    if kind == "ibm":
        arg = f"{arg} (live calibration)"
    cm = tg.build_coupling_map()
    ops = [o for o in tg.operation_names if o not in ("measure", "reset", "delay", "if_else", "for_loop", "switch_case", "while_loop")]
    d = {"spec": spec, "coupling_map": arg, "num_qubits": tg.num_qubits, "num_edges": len(cm.get_edges()) // 2, "basis_gates": sorted(ops)}
    if id(tg) in PRUNE_INFO:
        d["pruned_couplers"] = len(PRUNE_INFO[id(tg)]["removed"]); d["prune_max_error"] = PRUNE_INFO[id(tg)]["max_error"]
    return d
