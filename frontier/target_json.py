"""A device Target as plain JSON and back, so a live calibration can travel between machines with
different package versions (the Mac's qiskit-ibm-runtime and Colab's differ; a pickled Target would not load).

Kept: number of qubits, dt, every instruction's per-qubit error and duration, and each qubit's T1/T2.
That is all the compilers and the damage model read.
"""
from __future__ import annotations

import json


def target_to_json(target) -> dict:
    ops = {}
    for name in target.operation_names:
        props = target[name]
        if props is None or set(props) == {None}:
            ops[name] = None
            continue
        ops[name] = [[list(q), None if p is None else p.error, None if p is None else p.duration]
                     for q, p in props.items() if q is not None]
    qp = []
    for p in (target.qubit_properties or []):
        qp.append(None if p is None else {"t1": getattr(p, "t1", None), "t2": getattr(p, "t2", None),
                                          "frequency": getattr(p, "frequency", None)})
    return {"num_qubits": target.num_qubits, "dt": target.dt, "ops": ops, "qubit_properties": qp or None}


def _gate(name: str):
    from qiskit.circuit import Delay, Measure, Parameter, Reset
    from qiskit.circuit.library import CXGate, CZGate, ECRGate, IGate, RZGate, RZZGate, SXGate, XGate
    fixed = {"cz": CZGate(), "cx": CXGate(), "ecr": ECRGate(), "sx": SXGate(), "x": XGate(), "id": IGate(),
             "measure": Measure(), "reset": Reset()}
    if name in fixed:
        return fixed[name]
    if name == "rz":
        return RZGate(Parameter("theta"))
    if name == "rzz":
        return RZZGate(Parameter("theta"))
    if name == "delay":
        return Delay(Parameter("t"))
    return None  # control flow and anything unknown is skipped


def target_from_json(d: dict):
    from qiskit.providers import QubitProperties
    from qiskit.transpiler import InstructionProperties, Target
    qp = None
    if d.get("qubit_properties"):
        qp = [QubitProperties(**{k: v for k, v in (p or {}).items() if v is not None}) for p in d["qubit_properties"]]
    t = Target(num_qubits=d["num_qubits"], dt=d["dt"], qubit_properties=qp)
    for name, entries in d["ops"].items():
        g = _gate(name)
        if g is None:
            continue
        if entries is None:
            t.add_instruction(g, name=name)
        else:
            t.add_instruction(g, {tuple(q): InstructionProperties(error=e, duration=du) for q, e, du in entries}, name=name)
    return t


def save(target, path) -> None:
    from pathlib import Path
    Path(path).write_text(json.dumps(target_to_json(target)))


def load(path):
    from pathlib import Path
    return target_from_json(json.loads(Path(path).read_text()))
