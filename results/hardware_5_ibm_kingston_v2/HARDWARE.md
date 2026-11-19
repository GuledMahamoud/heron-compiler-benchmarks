# Real chip: ours vs Qiskit on ibm_kingston, job dbvccleps3fc73bk7sng, 8000 shots each

Score: fraction of shots in the ideal electron sector (an ideal chip gives 1.0; a uniformly random 64-bit string is in the (16, 16) sector with probability C(32,16)^2 / 2^64, about 2%). Higher is better. ± is one standard error from the shot count.

| circuit | variant | 2q gates | predicted damage | in-sector fraction |
|---|---|---:|---:|---:|
| anderson_momentum_trotter-1 | qiskit | 780 | 5.402 | 0.0576 ± 0.0026 |
| anderson_momentum_trotter-1 | qiskit_2 | 787 | 5.077 | 0.0389 ± 0.0022 |
| anderson_momentum_trotter-1 | ours | 599 | 3.429 | 0.0715 ± 0.0029 |
| anderson_momentum_trotter-1 | ours_2 | 675 | 3.867 | 0.0616 ± 0.0027 |

- **anderson_momentum_trotter-1**: ours pair mean 0.0666 vs qiskit pair mean 0.0483 (ratio 1.38x; both ours above both qiskit: yes)
