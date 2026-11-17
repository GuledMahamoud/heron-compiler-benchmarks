"""Is a compiled circuit runnable on a device?  Native gates, coupled pairs, and no dead hardware."""
from __future__ import annotations


def conformance(out, target) -> str | None:
    """None when `out` is runnable on `target`, else the reason it is not."""
    if out.num_qubits != target.num_qubits:
        return f"output has {out.num_qubits} qubits, target has {target.num_qubits}"
    if out.layout is None:
        return "output circuit has no layout (return a circuit from a pass manager with a layout stage)"
    names = set(target.operation_names)
    for inst in out.data:
        name = inst.operation.name
        if name == "barrier":
            continue
        qargs = tuple(out.find_bit(q).index for q in inst.qubits)
        if name not in names:
            return f"gate '{name}' is not native to the target"
        if not target.instruction_supported(name, qargs):
            return f"gate '{name}' on qubits {qargs} is not supported by the target"
    dead = dead_elements(out, _calibration(target))
    if dead:
        return "uses qubits or couplers the calibration marks unusable (error >= 0.5): " + ", ".join(dead[:6])
    return None


_CAL: dict[int, tuple] = {}


def _calibration(target):
    if id(target) not in _CAL:
        from harness.damage import from_target
        _CAL[id(target)] = (target, from_target(target, "conformance"))  # keep target alive so id() stays unique
    return _CAL[id(target)][1]


def dead_elements(circ, cal) -> list[str]:
    """Couplers and qubits this circuit uses that the calibration marks unusable (error >= 0.5, T1 < 10 us,
    or readout error >= 0.5 on a measured qubit).  A compiler that routes through them is not runnable."""
    from harness.damage import DEAD, MIN_T1
    bad = set()
    for inst in circ.data:
        if inst.operation.name == "barrier":
            continue
        qs = [circ.find_bit(q).index for q in inst.qubits]
        if len(qs) == 2:
            c = cal.coupler.get(cal.edge(*qs))
            if c is None or c["error"] >= DEAD:
                bad.add(f"coupler {cal.edge(*qs)}")
        for q in qs:
            pq = cal.qubit[str(q)]
            if pq["sx_error"] >= DEAD or pq["t1"] < MIN_T1:
                bad.add(f"qubit {q}")
    if circ.layout is not None:
        for q in circ.layout.final_index_layout(filter_ancillas=True):
            if cal.qubit[str(q)]["readout_error"] >= DEAD:
                bad.add(f"readout {q}")
    return sorted(bad)
