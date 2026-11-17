# Relative-phase Toffoli rewrite on its own

our compiler's compute/uncompute pair rewrite, then Qiskit 2.6 level 3, best of 32 seeds by two-qubit gates, proven against the original source. Baseline: the same without the rewrite. Target FakeTorino.

| circuit | split | baseline 2q | with rewrite | change | 2q depth (base / rewrite) | verification |
|---|---|---:|---:|---:|---:|---|
| adder_n10 | train | 93 | 83 | -10.8% | 84 / 74 | equivalent |
| bigadder_n18 | train | 208 | 205 | -1.4% | 147 / 145 | equivalent_up_to_global_phase |
| multiplier_n15 | train | 421 | 319 | -24.2% | 243 / 199 | equivalent_up_to_global_phase |
| qf21_n15 | test | 225 | 216 | -4.0% | 196 / 193 | equivalent_up_to_global_phase |
| qpe_n9 | test | 69 | 60 | -13.0% | 62 / 54 | equivalent_up_to_global_phase |
| sat_n11 | train | 445 | 263 | -40.9% | 354 / 204 | equivalent_up_to_global_phase |
| sat_n7 | test | 95 | 90 | -5.3% | 73 / 71 | equivalent_up_to_global_phase |

25 of 32 circuits contain no rewritable pair and are unchanged.
