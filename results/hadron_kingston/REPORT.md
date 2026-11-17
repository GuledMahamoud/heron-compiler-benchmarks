# Frontier test — 2026-11-16 23:01

Target `fake:FakeKingston`; programs: ours.py; Qiskit best of 32 seeds; program seeds 1; limit 7200 s.  Level 1 = verified, and at least 10% fewer two-qubit gates than the best of Qiskit, the AI transpiler and the circuit as published.

## x_100_meson.qasm (120 qubits, 14170 two-qubit gates in the source)

| compiler | status | 2q gates | 2q depth | duration (ns) | predicted damage | seconds | check |
|---|---|---:|---:|---:|---:|---:|---|
| qiskit | proven | 15352 | 739 | 77036 | 68.110 | 358.4 | qcec equivalent_up_to_global_phase |
| ours s0 | proven | 17218 | 1097 | 115048 | 83.958 | 147.9 | qcec equivalent_up_to_global_phase |

**not better: ours s0 17218 two-qubit gates vs 15352 (-12%)**

