# Real chip: ours vs Qiskit on ibm_marrakesh, job dbu1v749po4c73ceeh20, 8000 shots each

Score: fraction of shots in the ideal electron sector (an ideal chip gives 1.0; a uniformly random 64-bit string is in the (16, 16) sector with probability C(32,16)^2 / 2^64, about 2%). Higher is better. ± is one standard error from the shot count.

| circuit | variant | 2q gates | predicted damage | in-sector fraction |
|---|---|---:|---:|---:|
| anderson_momentum_trotter-1 | qiskit | 803 | 8.159 | 0.0217 ± 0.0016 |
| anderson_momentum_trotter-1 | qiskit_2 | 782 | 8.336 | 0.0344 ± 0.0020 |
| anderson_momentum_trotter-1 | ours | 666 | 6.832 | 0.0465 ± 0.0024 |
| anderson_momentum_trotter-1 | ours_2 | 797 | 6.839 | 0.0259 ± 0.0018 |

- **anderson_momentum_trotter-1**: ours pair mean 0.0362 vs Qiskit pair mean 0.0281 (ratio 1.29x; both ours above both Qiskit: no)
