# Frontier test — 2026-11-22 16:09

Target `fake:FakeKingston`; programs: ours.py; Qiskit best of 32 seeds; program seeds 3; limit 1800 s.  Level 1 = verified, and at least 10% fewer two-qubit gates than the best of Qiskit, the AI transpiler and the circuit as published.

## x_100_meson.qasm (120 qubits, 14170 two-qubit gates in the source)

| compiler | status | 2q gates | 2q depth | duration (ns) | predicted damage | seconds | check |
|---|---|---:|---:|---:|---:|---:|---|
| qiskit | proven | 15352 | 739 | 77036 | 68.110 | 263.1 | qcec equivalent_up_to_global_phase |
| ours s0 | proven | 15745 | 714 | 75316 | 74.394 | 915.1 | qcec equivalent_up_to_global_phase |
| ours s1 | proven | 15352 | 739 | 77036 | 68.110 | 881.6 | qcec equivalent_up_to_global_phase |
| ours s2 | proven | 15352 | 739 | 77036 | 68.110 | 908.5 | qcec equivalent_up_to_global_phase |

**not better: ours s1 15352 two-qubit gates vs 15352 (+0%)**

