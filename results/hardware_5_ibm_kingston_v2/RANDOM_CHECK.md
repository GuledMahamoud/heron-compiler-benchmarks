# Random-input check — 2026-11-19 10:17

Return fidelity on random product inputs (1.0 = output matches the source on that input). MPS simulator, bond cap 256; compare rows of the same circuit side by side. The BROKEN row is a negative control with one two-qubit gate removed: it should score clearly lower.

| circuit | compiler | qubits | states | min fidelity | mean fidelity | minutes |
|---|---|---:|---:|---:|---:|---:|
| anderson_momentum_trotter-1 | ours | 65 | 2 | 1.000000 | 1.000000 | 10.0 |
| anderson_momentum_trotter-1 | ours_2 | 68 | 2 | 1.000000 | 1.000000 | 1.4 |
| anderson_momentum_trotter-1 | ours BROKEN (control) | 65 | 2 | 0.636917 | 0.660816 | 18.6 |
