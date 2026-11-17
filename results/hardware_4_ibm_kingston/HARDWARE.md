# Real chip: ours vs Qiskit on ibm_kingston, job dbuatj782tmc73dt1q30, 8000 shots each

Score: fraction of shots in the ideal electron sector (an ideal chip gives 1.0; a uniformly random 64-bit string is in the (16, 16) sector with probability C(32,16)^2 / 2^64, about 2%). Higher is better. ± is one standard error from the shot count.

| circuit | variant | 2q gates | predicted damage | in-sector fraction |
|---|---|---:|---:|---:|
| anderson_momentum_trotter-1 | qiskit | 829 | 5.060 | 0.0519 ± 0.0025 |
| anderson_momentum_trotter-1 | qiskit_2 | 925 | 5.313 | 0.0331 ± 0.0020 |
| anderson_momentum_trotter-1 | ours | 742 | 4.605 | 0.0498 ± 0.0024 |
| anderson_momentum_trotter-1 | ours_2 | 802 | 4.693 | 0.0391 ± 0.0022 |

- **anderson_momentum_trotter-1**: ours pair mean 0.0444 vs qiskit pair mean 0.0425 (ratio 1.05x; both ours above both qiskit: no)
