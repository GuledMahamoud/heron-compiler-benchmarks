# Frontier test — 2026-11-16 23:43

Target `fake:FakeFez`; programs: ours.py; Qiskit best of 32 seeds; program seeds 1; limit 1800 s.  Level 1 = verified, and at least 10% fewer two-qubit gates than the best of Qiskit, the AI transpiler and the circuit as published.

## anderson_momentum_trotter-1.qpy (64 qubits, 254 two-qubit gates in the source)

| compiler | status | 2q gates | 2q depth | duration (ns) | predicted damage | seconds | check |
|---|---|---:|---:|---:|---:|---:|---|
| qiskit | unverified | 953 | 84 | 9840 | 7.812 | 30.0 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ai | unverified | 692 | 73 | 8508 | 7.474 | 34.8 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s0 | unverified | 729 | 79 | 9276 | 7.785 | 114.9 | undecided in 120 s (timeout); no statevector check above 20 qubits |

**no verified comparison**

## anderson_momentum_trotter-3.qpy (64 qubits, 734 two-qubit gates in the source)

| compiler | status | 2q gates | 2q depth | duration (ns) | predicted damage | seconds | check |
|---|---|---:|---:|---:|---:|---:|---|
| qiskit | unverified | 1957 | 227 | 26364 | 17.030 | 69.4 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ai | unverified | 2037 | 232 | 26664 | 22.027 | 58.7 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s0 | unverified | 1972 | 203 | 23604 | 15.459 | 114.5 | undecided in 120 s (timeout); no statevector check above 20 qubits |

**no verified comparison**

## anderson_momentum_trotter-7.qpy (64 qubits, 1694 two-qubit gates in the source)

| compiler | status | 2q gates | 2q depth | duration (ns) | predicted damage | seconds | check |
|---|---|---:|---:|---:|---:|---:|---|
| qiskit | unverified | 4310 | 468 | 53208 | 30.789 | 145.9 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ai | unverified | 5250 | 545 | 61812 | 45.827 | 226.5 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s0 | unverified | 4310 | 468 | 53040 | 30.347 | 113.8 | undecided in 120 s (timeout); no statevector check above 20 qubits |

**no verified comparison**

