# Frontier test — 2026-11-16 20:41

Target `fake:FakeMarrakesh`; programs: ours.py; Qiskit best of 32 seeds; program seeds 1; limit 1800 s.  Level 1 = verified, and at least 10% fewer two-qubit gates than the best of Qiskit, the AI transpiler and the circuit as published.

## floquet_mixed_field_ising_mag_51qx16c.qasm (51 qubits, 896 two-qubit gates in the source)

| compiler | status | 2q gates | 2q depth | duration (ns) | predicted damage | seconds | check |
|---|---|---:|---:|---:|---:|---:|---|
| qiskit | unverified | 4095 | 535 | 59828 | 27.074 | 42.9 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s0 | unverified | 3512 | 401 | 46340 | 25.979 | 115.0 | undecided in 120 s (timeout); no statevector check above 20 qubits |

**no verified comparison**

