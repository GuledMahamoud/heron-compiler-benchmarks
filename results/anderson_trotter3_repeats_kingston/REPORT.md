# Frontier test — 2026-11-17 06:05

Target `fake:FakeKingston`; programs: ours.py; Qiskit best of 32 seeds; program seeds 5; limit 1800 s.  Level 1 = verified, and at least 10% fewer two-qubit gates than the best of Qiskit, the AI transpiler and the circuit as published.

## anderson_momentum_trotter-3.qasm (64 qubits, 734 two-qubit gates in the source)

| compiler | status | 2q gates | 2q depth | duration (ns) | predicted damage | seconds | check |
|---|---|---:|---:|---:|---:|---:|---|
| qiskit | unverified | 1849 | 228 | 24848 | 10.542 | 67.2 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s0 | unverified | 1866 | 211 | 23500 | 9.026 | 115.0 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s1 | unverified | 2012 | 216 | 23328 | 9.450 | 114.8 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s2 | unverified | 1891 | 221 | 24520 | 9.297 | 115.7 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s3 | unverified | 1871 | 233 | 25348 | 9.897 | 115.8 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s4 | unverified | 1755 | 205 | 21620 | 8.473 | 116.0 | undecided in 120 s (timeout); no statevector check above 20 qubits |

**no verified comparison**

