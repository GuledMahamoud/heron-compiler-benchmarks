# Random-input check — 2026-11-18 01:57

Return fidelity on random product inputs (1.0 = output matches the source on that input). MPS simulator, bond cap 256; compare rows of the same circuit side by side. The BROKEN row is a negative control with one two-qubit gate removed: it should score clearly lower.

| circuit | compiler | qubits | states | min fidelity | mean fidelity | minutes |
|---|---|---:|---:|---:|---:|---:|
| anderson_momentum_trotter-1 | ours | 66 | 2 | 1.000000 | 1.000000 | 124.2 |
| anderson_momentum_trotter-1 | ours_2 | 67 | 2 | 1.000000 | 1.000000 | 10.4 |
| anderson_momentum_trotter-1 | qiskit | 69 | 2 | 1.000000 | 1.000000 | 2.5 |
| anderson_momentum_trotter-1 | qiskit_2 | 65 | 2 | 1.000000 | 1.000000 | 1.7 |
| anderson_momentum_trotter-1 | ours BROKEN (control) | 66 | 2 | 0.260574 | 0.325660 | 109.9 |
