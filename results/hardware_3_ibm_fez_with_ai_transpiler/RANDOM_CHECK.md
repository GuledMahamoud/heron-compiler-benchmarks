# Random-input check — 2026-11-17 16:50

Return fidelity on random product inputs (1.0 = output matches the source on that input). MPS simulator, bond cap 256; compare rows of the same circuit side by side. The BROKEN row is a negative control with one two-qubit gate removed: it should score clearly lower.

| circuit | compiler | qubits | states | min fidelity | mean fidelity | minutes |
|---|---|---:|---:|---:|---:|---:|
| anderson_momentum_trotter-1 | ours | 66 | 2 | 1.000000 | 1.000000 | 77.2 |
| anderson_momentum_trotter-1 | ours_2 | 66 | 2 | 1.000000 | 1.000000 | 18.1 |
