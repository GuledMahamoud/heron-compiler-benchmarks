# Random-input check — 2026-11-19 12:42

Return fidelity on random product inputs (1.0 = output matches the source on that input). MPS simulator, bond cap 256; compare rows of the same circuit side by side. The BROKEN row is a negative control with one two-qubit gate removed: it should score clearly lower.

| circuit | compiler | qubits | states | min fidelity | mean fidelity | minutes |
|---|---|---:|---:|---:|---:|---:|
| adder_n28 | ours | 28 | 2 | 1.000000 | 1.000000 | 0.0 |
| adder_n28 | ours_2 | 28 | 2 | 1.000000 | 1.000000 | 0.0 |
| adder_n28 | ours BROKEN (control) | 28 | 2 | 0.164018 | 0.231009 | 0.0 |
