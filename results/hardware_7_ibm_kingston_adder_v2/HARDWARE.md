# Real chip: ours vs Qiskit on ibm_kingston, job dbven1pcn7vc73egp3vg, 8000 shots each

Score: fraction of shots equal to the one correct output (an ideal chip gives 1.0; a random bit string matches with probability 2^-n). Higher is better. ± is one standard error from the shot count.

| circuit | variant | 2q gates | predicted damage | correct-output fraction |
|---|---|---:|---:|---:|
| adder_n28 | qiskit | 340 | 2.999 | 0.0047 ± 0.0008 |
| adder_n28 | qiskit_2 | 337 | 2.673 | 0.0139 ± 0.0013 |
| adder_n28 | ours | 230 | 1.635 | 0.0744 ± 0.0029 |
| adder_n28 | ours_2 | 252 | 1.601 | 0.0159 ± 0.0014 |

- **adder_n28**: ours pair mean 0.0451 vs qiskit pair mean 0.0093 (ratio 4.85x; both ours above both qiskit: yes)
