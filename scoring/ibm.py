"""IBM Quantum access: the saved account, and measuring a compiled circuit's logical qubits."""
from __future__ import annotations


def service():
    """The IBM Quantum account saved with QiskitRuntimeService.save_account(...)."""
    from qiskit_ibm_runtime import QiskitRuntimeService
    return QiskitRuntimeService()


def measured_copy(circ):
    """Measure each logical qubit at its final physical site into the clbit of the same index."""
    from qiskit import ClassicalRegister
    final = circ.layout.final_index_layout(filter_ancillas=True)
    out = circ.copy()
    cr = ClassicalRegister(len(final), "m")
    out.add_register(cr)
    for l, p in enumerate(final):
        out.measure(p, cr[l])
    return out
