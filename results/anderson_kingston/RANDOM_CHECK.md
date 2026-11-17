# Random-input check — 2026-11-17 05:28

Return fidelity on random product inputs (1.0 = output matches the source on that input). MPS simulator, bond cap 256; compare rows of the same circuit side by side. The BROKEN row is a negative control with one two-qubit gate removed: it should score clearly lower.

| circuit | compiler | qubits | states | min fidelity | mean fidelity | minutes |
|---|---|---:|---:|---:|---:|---:|
| anderson_momentum_trotter-1 | ours_s0 | 64 | 6 | 1.000000 | 1.000000 | 98.9 |
| anderson_momentum_trotter-1 | qiskit | 65 | 6 | 1.000000 | 1.000000 | 130.6 |
| anderson_momentum_trotter-1 | ours_s0 BROKEN (control) | 64 | 6 | 0.011892 | 0.349802 | 101.1 |
