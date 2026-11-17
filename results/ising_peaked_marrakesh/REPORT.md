# Frontier test — 2026-11-16 20:22

Target `fake:FakeMarrakesh`; programs: ours.py; Qiskit best of 8 seeds; program seeds 1; limit 1800 s.  Level 1 = verified, and at least 10% fewer two-qubit gates than the best of Qiskit, the AI transpiler and the circuit as published.

## floquet_mixed_field_ising_mag_51qx16c.qasm (51 qubits, 896 two-qubit gates in the source)

| compiler | status | 2q gates | 2q depth | duration (ns) | predicted damage | seconds | check |
|---|---|---:|---:|---:|---:|---:|---|
| qiskit | unverified | 4459 | 594 | 65832 | 30.681 | 12.3 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s0 | unverified | 3514 | 405 | 46332 | 25.988 | 115.9 | undecided in 120 s (timeout); no statevector check above 20 qubits |

**no verified comparison**

## peaked_circuit_P9_Hqap_56x1917.qasm (56 qubits, 1917 two-qubit gates in the source)

| compiler | status | 2q gates | 2q depth | duration (ns) | predicted damage | seconds | check |
|---|---|---:|---:|---:|---:|---:|---|
| qiskit | unverified | 26092 | 3577 | 377276 | 124.659 | 41.2 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s0 | unverified | 26210 | 3734 | 394204 | 128.467 | 120.0 | undecided in 120 s (timeout); no statevector check above 20 qubits |

**no verified comparison**

