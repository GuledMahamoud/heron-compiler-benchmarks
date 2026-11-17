# Real chip: ours vs Qiskit on ibm_fez, job dbu2rtgvv3fc73c0nhbg, 8000 shots each

Score: fraction of shots in the ideal electron sector (an ideal chip gives 1.0; a uniformly random 64-bit string is in the (16, 16) sector with probability C(32,16)^2 / 2^64, about 2%). Higher is better. ± is one standard error from the shot count.

| circuit | variant | 2q gates | predicted damage | in-sector fraction |
|---|---|---:|---:|---:|
| anderson_momentum_trotter-1 | qiskit | 916 | 7.213 | 0.0344 ± 0.0020 |
| anderson_momentum_trotter-1 | qiskit_2 | 839 | 7.506 | 0.0243 ± 0.0017 |
| anderson_momentum_trotter-1 | ours | 778 | 6.003 | 0.0344 ± 0.0020 |
| anderson_momentum_trotter-1 | ours_2 | 807 | 6.429 | 0.0305 ± 0.0019 |
| anderson_momentum_trotter-1 | ai | 742 | 12.615 | 0.0165 ± 0.0014 |
| anderson_momentum_trotter-1 | ai_2 | 740 | 9.915 | 0.0305 ± 0.0019 |

- **anderson_momentum_trotter-1**: ours pair mean 0.0324 vs qiskit pair mean 0.0293 (ratio 1.11x; both ours above both qiskit: no)
- **anderson_momentum_trotter-1**: ours pair mean 0.0324 vs ai pair mean 0.0235 (ratio 1.38x; both ours above both ai: no)
