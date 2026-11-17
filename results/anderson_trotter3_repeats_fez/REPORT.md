# Frontier test — 2026-11-17 06:42

Target `fake:FakeFez`; programs: ours.py; Qiskit best of 32 seeds; program seeds 5; limit 1800 s.  Level 1 = verified, and at least 10% fewer two-qubit gates than the best of Qiskit, the AI transpiler and the circuit as published.

## anderson_momentum_trotter-3.qasm (64 qubits, 734 two-qubit gates in the source)

| compiler | status | 2q gates | 2q depth | duration (ns) | predicted damage | seconds | check |
|---|---|---:|---:|---:|---:|---:|---|
| qiskit | unverified | 1957 | 227 | 26364 | 17.031 | 60.8 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s0 | unverified | 1972 | 203 | 23604 | 15.188 | 115.0 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s1 | unverified | 2038 | 221 | 25224 | 16.243 | 116.0 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s2 | unverified | 1672 | 176 | 20448 | 13.455 | 115.8 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s3 | unverified | 1996 | 199 | 23340 | 15.532 | 116.2 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s4 | unverified | 1888 | 238 | 28488 | 16.624 | 116.1 | undecided in 120 s (timeout); no statevector check above 20 qubits |

**no verified comparison**

