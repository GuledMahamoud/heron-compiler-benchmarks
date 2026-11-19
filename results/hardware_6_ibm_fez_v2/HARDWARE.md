# Real chip: ours vs Qiskit on ibm_fez, job dbvd49n82tmc73durir0, 8000 shots each

Score: fraction of shots in the ideal electron sector (an ideal chip gives 1.0; a uniformly random 64-bit string is in the (16, 16) sector with probability C(32,16)^2 / 2^64, about 2%). Higher is better. ± is one standard error from the shot count.

| circuit | variant | 2q gates | predicted damage | in-sector fraction |
|---|---|---:|---:|---:|
| anderson_momentum_trotter-1 | qiskit | 791 | 6.465 | 0.0405 ± 0.0022 |
| anderson_momentum_trotter-1 | qiskit_2 | 749 | 7.290 | 0.0424 ± 0.0023 |
| anderson_momentum_trotter-1 | ours | 718 | 5.828 | 0.0506 ± 0.0025 |
| anderson_momentum_trotter-1 | ours_2 | 619 | 5.470 | 0.0432 ± 0.0023 |

- **anderson_momentum_trotter-1**: ours pair mean 0.0469 vs qiskit pair mean 0.0414 (ratio 1.13x; both ours above both qiskit: yes)
