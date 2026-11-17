"""Discover and load QASMBench circuits.

Layout on disk: QASMBench/<suite>/<name>/<name>.qasm.  The *_transpiled.qasm siblings that
QASMBench ships are ignored; we do our own compilation.

Loading uses Qiskit's OpenQASM 2 parser with the *legacy* gate set, because QASMBench was written
against the old Qiskit qelib1.inc (cu1, rccx, c3x, ...).  After loading we strip barriers and
*final* measurements: they carry no computation and every tool treats them differently.  Mid-circuit
measurements, resets and classical conditions are kept -- they are part of the computation -- and the
record marks such circuits `nonunitary` so verification outcomes can be read in context.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from qiskit import QuantumCircuit, qasm2
from qiskit.circuit import ControlFlowOp

ROOT = Path(__file__).resolve().parent.parent
QASMBENCH = ROOT / "QASMBench"
SUITES = ("small", "medium", "large")

_QREG = re.compile(r"^\s*qreg\s+\w+\s*\[\s*(\d+)\s*\]", re.M)


@dataclass(frozen=True)
class Benchmark:
    name: str
    suite: str
    path: Path
    declared_qubits: int  # summed qreg sizes, read with a regex so listing stays cheap

    @property
    def rel_path(self) -> str:
        return str(self.path.relative_to(ROOT))


def declared_qubits(path: Path) -> int:
    return sum(int(m) for m in _QREG.findall(path.read_text(errors="replace")))


_SKIP_PREFIX = ("//", "OPENQASM", "include", "qreg", "creg", "measure", "barrier", "gate", "}", "{")


def approx_statements(path: Path) -> int:
    """Number of gate-like statements, counted by line without parsing (an 85 MB file takes seconds)."""
    n = 0
    with open(path, errors="replace") as f:
        for line in f:
            if ";" in line and not line.lstrip().startswith(_SKIP_PREFIX):
                n += 1
    return n


def discover(suites=("small", "medium"), max_qubits: int | None = None,
             only: list[str] | None = None, exclude: list[str] | None = None,
             root: Path = QASMBENCH) -> list[Benchmark]:
    """All <suite>/<name>/<name>.qasm under `root`, filtered, sorted by (declared qubits, name)."""
    found: list[Benchmark] = []
    for suite in suites:
        for d in sorted((root / suite).iterdir()):
            f = d / f"{d.name}.qasm"
            if not f.is_file():
                continue
            if only and d.name not in only:
                continue
            if exclude and d.name in exclude:
                continue
            n = declared_qubits(f)
            if max_qubits is not None and n > max_qubits:
                continue
            found.append(Benchmark(d.name, suite, f, n))
    found.sort(key=lambda b: (b.declared_qubits, b.name))
    return found


_MEASURE = re.compile(r"^\s*measure\s+(\w+)\s*(\[\s*\d+\s*\])?\s*->\s*(\w+)")
_DECL = re.compile(r"^\s*[qc]reg\s+(\w+)\s*\[", re.M)


def load(bench: Benchmark) -> QuantumCircuit:
    try:
        qc = qasm2.load(str(bench.path), custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    except qasm2.QASM2ParseError as e:
        # QASMBench quirk (hhl_n14): a trailing `measure q[i] -> c[i];` on registers that were never
        # declared.  Final measurements are stripped anyway, so drop just those lines and retry.
        if "is not defined in this scope" not in str(e):
            raise
        text = bench.path.read_text(errors="replace")
        declared = set(_DECL.findall(text))
        kept = [ln for ln in text.splitlines()
                if not ((m := _MEASURE.match(ln)) and (m.group(1) not in declared or m.group(3) not in declared))]
        if len(kept) == text.count("\n") + 1:
            raise
        qc = qasm2.loads("\n".join(kept), custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    qc.name = bench.name
    return qc


def prepare(qc: QuantumCircuit) -> QuantumCircuit:
    """Copy without final measurements (and the classical bits they fed) or barriers."""
    qc = qc.copy()
    qc.remove_final_measurements(inplace=True)
    out = qc.copy_empty_like()
    for inst in qc.data:
        if inst.operation.name != "barrier":
            out.append(inst.operation, inst.qubits, inst.clbits, copy=False)
    return out


def is_two_qubit(inst) -> bool:
    return inst.operation.num_qubits == 2 and inst.operation.name not in ("barrier", "measure")


def stats(qc: QuantumCircuit) -> dict:
    """Size metrics for one circuit; identical keys for the original and every compiled output."""
    ops = {k: int(v) for k, v in qc.count_ops().items()}
    nonunitary = any(
        inst.operation.name in ("measure", "reset") or isinstance(inst.operation, ControlFlowOp)
        for inst in qc.data
    )
    return {
        "qubits": qc.num_qubits,
        "gates": qc.size(),
        "two_qubit": sum(1 for inst in qc.data if is_two_qubit(inst)),
        "depth": qc.depth(),
        "depth_2q": qc.depth(filter_function=is_two_qubit),
        "ops": ops,
        "nonunitary": nonunitary,
    }
