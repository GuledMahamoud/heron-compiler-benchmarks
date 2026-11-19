# Real chip: ours vs Qiskit on ibm_fez, job dbveu39cn7vc73egpcj0, 8000 shots each

Score: fraction of shots equal to the one correct output (an ideal chip gives 1.0; a random bit string matches with probability 2^-n). Higher is better. ± is one standard error from the shot count.

| circuit | variant | 2q gates | predicted damage | correct-output fraction |
|---|---|---:|---:|---:|
| adder_n28 | qiskit | 344 | 3.574 | 0.0005 ± 0.0002 |
| adder_n28 | qiskit_2 | 356 | 3.825 | 0.0018 ± 0.0005 |
| adder_n28 | ours | 222 | 2.157 | 0.0334 ± 0.0020 |
| adder_n28 | ours_2 | 234 | 2.235 | 0.0396 ± 0.0022 |

- **adder_n28**: ours pair mean 0.0365 vs qiskit pair mean 0.0011 (ratio 32.44x; both ours above both qiskit: yes)
