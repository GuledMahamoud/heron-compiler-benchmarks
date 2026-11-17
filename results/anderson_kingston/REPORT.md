# Frontier test — 2026-11-16 21:36

Target `fake:FakeKingston`; programs: ours.py; Qiskit best of 32 seeds; program seeds 1; limit 1800 s.  Level 1 = verified, and at least 10% fewer two-qubit gates than the best of Qiskit, the AI transpiler and the circuit as published.

## anderson_momentum_trotter-1.qasm (64 qubits, 254 two-qubit gates in the source)

| compiler | status | 2q gates | 2q depth | duration (ns) | predicted damage | seconds | check |
|---|---|---:|---:|---:|---:|---:|---|
| qiskit | unverified | 829 | 98 | 10760 | 5.387 | 31.9 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s0 | unverified | 764 | 82 | 9000 | 4.357 | 115.8 | undecided in 120 s (timeout); no statevector check above 20 qubits |

**no verified comparison**

## anderson_momentum_trotter-3.qasm (64 qubits, 734 two-qubit gates in the source)

| compiler | status | 2q gates | 2q depth | duration (ns) | predicted damage | seconds | check |
|---|---|---:|---:|---:|---:|---:|---|
| qiskit | unverified | 1849 | 228 | 24848 | 10.542 | 59.8 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s0 | unverified | 1891 | 197 | 22032 | 8.849 | 115.8 | undecided in 120 s (timeout); no statevector check above 20 qubits |

**no verified comparison**

## anderson_momentum_trotter-7.qasm (64 qubits, 1694 two-qubit gates in the source)

| compiler | status | 2q gates | 2q depth | duration (ns) | predicted damage | seconds | check |
|---|---|---:|---:|---:|---:|---:|---|
| qiskit | unverified | 4391 | 443 | 48492 | 20.057 | 119.7 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s0 | unverified | 4161 | 469 | 51188 | 18.167 | 116.1 | undecided in 120 s (timeout); no statevector check above 20 qubits |

**no verified comparison**

