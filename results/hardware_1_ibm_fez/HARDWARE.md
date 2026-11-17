# Real chip: ours vs Qiskit on ibm_fez, job dbu1o1ovv3fc73c0m59g, 4000 shots each

Score: fraction of shots in the ideal electron sector (an ideal chip gives 1.0; a uniformly random 64-bit string is in the (16, 16) sector with probability C(32,16)^2 / 2^64, about 2%). Higher is better. ± is one standard error from the shot count.

| circuit | variant | 2q gates | predicted damage | in-sector fraction |
|---|---|---:|---:|---:|
| anderson_momentum_trotter-1 | qiskit | 916 | 7.213 | 0.0355 ± 0.0029 |
| anderson_momentum_trotter-1 | qiskit_2 | 839 | 7.506 | 0.0185 ± 0.0021 |
| anderson_momentum_trotter-1 | ours | 781 | 5.808 | 0.0418 ± 0.0032 |
| anderson_momentum_trotter-1 | ours_2 | 779 | 5.728 | 0.0393 ± 0.0031 |
| anderson_momentum_trotter-3 | qiskit | 1773 | 13.823 | 0.0210 ± 0.0023 |
| anderson_momentum_trotter-3 | qiskit_2 | 2018 | 14.419 | 0.0185 ± 0.0021 |
| anderson_momentum_trotter-3 | ours | 1688 | 11.968 | 0.0232 ± 0.0024 |
| anderson_momentum_trotter-3 | ours_2 | 1819 | 11.841 | 0.0210 ± 0.0023 |

- **anderson_momentum_trotter-1**: ours pair mean 0.0405 vs Qiskit pair mean 0.0270 (ratio 1.50x; both ours above both Qiskit: yes)
- **anderson_momentum_trotter-3**: ours pair mean 0.0221 vs Qiskit pair mean 0.0198 (ratio 1.12x; both ours above both Qiskit: no)
