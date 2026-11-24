# Testing a quantum compiler on frontier circuits and IBM hardware

This repository holds the test harness, the results and one compiler pass from an independent project:
a compiler for IBM quantum chips, tested against Qiskit and IBM's AI transpiler on circuits from
published quantum research, and on IBM's real hardware.

The compiler itself was found with an AI-assisted search that I run privately; its source is not
included. Everything needed to **check** the results is: every compiled circuit, the circuits they came
from, the scripts that scored and verified them, and the hardware job results.

*Status: work in progress, November 2026. Not peer-reviewed. Numbers below are what I measured, with
their limits.*

## Latest: version 2 on real hardware (19 November 2026)

A newer version of the compiler, found by a later round of the same private search, places the circuit
in healthier parts of the chip and routes away from its noisiest connections. It was tested on two kinds
of circuit and two IBM chips, against Qiskit 2.6.2 at optimization level 3 (best of 32 seeds) compiled on
the same live calibration. Two compilations per compiler per run; 8,000 shots each. ± is one standard
error from the shot count. It leaves out drift between runs, which is larger (compare runs 1–4 below).

**Anderson trotter-1 (64 qubits).** Score = share of shots in the correct electron sector.

| Run | Chip | Version 2 | Qiskit | Predicted error, v2 vs Qiskit best |
|---|---|---|---|---|
| 5 | ibm_kingston | **7.15 ± 0.29%, 6.16 ± 0.27%** | 5.76 ± 0.26%, 3.89 ± 0.22% | 3.43 vs 5.08 |
| 6 | ibm_fez | **5.06 ± 0.25%, 4.32 ± 0.23%** | 4.24 ± 0.23%, 4.05 ± 0.22% | 5.47 vs 6.47 |

About 1.38× Qiskit on Kingston and 1.13× on Fez, each ± 0.06 (about 1.26× averaged).

**QASMBench adder_n28 (28 qubits, 24 Toffoli gates).** A classical reversible adder with exactly one
correct output (`1111000000000000111111111110`, qubit 0 rightmost); score = share of shots equal to it.
A random guess matches with probability 2^-28.

| Run | Chip | Version 2 | Qiskit | Predicted error, v2 vs Qiskit best |
|---|---|---|---|---|
| 7 | ibm_kingston | **7.44 ± 0.29%**, 1.59 ± 0.14% | 0.47 ± 0.08%, 1.39 ± 0.13% | 1.64 vs 2.67 |
| 8 | ibm_fez | **3.34 ± 0.20%, 3.96 ± 0.22%** | 0.05 ± 0.02%, 0.18 ± 0.05% | 2.16 vs 3.57 |

On Kingston the best version-2 compilation gave the right answer about 5× as often as Qiskit's best; the
second was only marginally ahead (within the noise), although the model predicted both alike. On Fez,
Qiskit's compilations almost never gave the right answer, while version 2 did 3–4% of the time.

**Summary.**
- Version 2 beat Qiskit in all 16 head-to-head comparisons (2 circuits × 2 chips × 2 × 2): 12 by more
  than two standard errors, while the other 4 are within shot noise (one each in runs 5 and 7, two in run 6).
- The size of the gain broadly followed the predicted error, but the model could not tell apart two
  similar compilations (adder, Kingston).
- All eight version-2 circuits that ran passed the random-input correctness check (1.000000); on every
  individual input, the broken controls scored 0.15 to 0.84 (four controls, eight inputs).
- Not everywhere: in simulation, version 2 on its own is **worse** than Qiskit on the 120-qubit hadron
  circuit (14% more two-qubit gates), where the circuit fills most of the chip. Qiskit's own level-3 output
  sits in the candidate pool, so on a circuit it cannot improve the compiler returns that output unchanged.
  That is what happens on hadron: 15,352 two-qubit gates, identical to Qiskit's compilation on every
  measure. It **matches** Qiskit there by handing back Qiskit's own work, which is a safe fallback and not
  a result. Runs 5–8 are unaffected: their circuits use under half the chip.
- Four runs, two circuits, two chips: a small sample, and absolute success rates on today's chips are low.

Runs 1–4 below used the first version.

## Results in short (first version)

**Circuits.** From the [Quantum Advantage Tracker](https://quantum-advantage-tracker.github.io/), mainly
the Anderson impurity model Trotter circuits (64 qubits) from the IBM / Oak Ridge National Laboratory /
University of Maryland submission. All comparisons use the same simulated or live calibration for every
compiler, with broken couplers and qubits removed for all of them. Every Qiskit compilation here used
Qiskit 2.6.2 (each compiled QPY file records the version that wrote it).

**Simulated chips** (predicted error = sum of gate, idle and readout error probabilities on the chip's
calibration; lower is better):

| Anderson circuit | Qiskit level 3, best of 32 | IBM AI transpiler | This compiler |
|---|---|---|---|
| trotter-1 (Kingston model) | 5.39 | – | **4.36** (19% lower) |
| trotter-3 (Kingston model) | 10.54 | – | **8.85** (16% lower) |
| trotter-7 (Kingston model) | 20.06 | – | **18.17** (9% lower) |
| trotter-1 (Fez model) | 7.81 | **7.47** | 7.79 |
| trotter-3 (Fez model) | 17.03 | 22.03 | **15.46** |
| trotter-7 (Fez model) | 30.79 | 45.83 | **30.35** |

- trotter-3, repeated with 5 seeds on each of two chip models: **all 10 runs** had lower predicted error
  than Qiskit's best of 32 (best: 21% lower error, 15% fewer two-qubit gates).
- Where it does **not** help: circuits already shaped to the chip (graph-state sampling, the Loschmidt-echo
  circuit, the Ising circuit on a healthy chip) are ties. On the 120-qubit hadron circuit it is
  **worse** than Qiskit (12% more two-qubit gates).

**Real IBM hardware** (Anderson trotter-1, 64 qubits). The circuit keeps 16 electrons in each spin half,
so a perfect run puts every shot in that sector, and a random bit string lands there about 2% of the
time. Score = share of shots in the right sector; two compilations per compiler per run. Qiskit settings
as for version 2 (level 3, best of 32 seeds, same live calibration); 4,000 shots per compilation in run 1
and 8,000 in runs 2–4; ± is one standard error from the shot count.

| Run | Chip | This compiler | Qiskit | IBM AI transpiler |
|---|---|---|---|---|
| 1 | ibm_fez | 4.18 ± 0.32%, 3.93 ± 0.31% | 3.55 ± 0.29%, 1.85 ± 0.21% | – |
| 2 | ibm_marrakesh | 4.65 ± 0.24%, 2.59 ± 0.18% | 2.17 ± 0.16%, 3.44 ± 0.20% | – |
| 3 | ibm_fez | 3.44 ± 0.20%, 3.05 ± 0.19% | 3.44 ± 0.20%, 2.43 ± 0.17% | 1.65 ± 0.14%, 3.05 ± 0.19% |
| 4 | ibm_kingston | 4.98 ± 0.24%, 3.91 ± 0.22% | 5.19 ± 0.25%, 3.31 ± 0.20% | – |

Averaged over the four runs, this compiler kept about **1.2×** as many in-sector shots as Qiskit
(3.8% vs 3.2%), and won 11 of 16 head-to-head comparisons (1 tie); 8 of the 11 wins, and 2 of the 4
losses, were larger than two standard errors. Against the AI transpiler (run 3 only)
about 1.4×. Run 4, on ibm_kingston, was close to a tie: Kingston gave higher scores to both compilers,
and the gap was within the noise. One possible reason is that the gain is smaller when a chip is in
better shape, as with the Ising circuit; more runs are needed to tell. The signal is small (everything is close to
the 2% random level), runs vary, and this is one circuit, so treat it as **early evidence**, not a
settled result. trotter-3 on hardware was indistinguishable from random for every compiler.

**Correctness.** Every circuit this compiler produced for the eight hardware runs (and Qiskit's for run 4) was
checked against the original on random input states with a matrix-product-state simulator: all scored 1.000000 (exact match to simulator
precision). A deliberately broken copy (one two-qubit gate removed) scored lower on every individual input:
0.08 to 0.84 across the six broken controls in these runs (13 inputs; runs 2 and 3 had none), and 0.01 to
0.98 in a separate 64-qubit check (`results/anderson_kingston`, six inputs). So the check does catch errors.
Smaller outputs are proven equivalent with
[MQT QCEC](https://github.com/cda-tum/mqt-qcec).

## Relative-phase Toffoli pairs

`toffoli/relative_phase.py` is a standalone Qiskit pass that replaces compute/uncompute Toffoli pairs with
3-CNOT relative-phase Toffolis when everything in between commutes with the leftover phase. The identity
is known (Barenco et al. 1995; Maslov 2016); the pass applies it automatically with a numerical safety
check. On benchmark circuits that contain such pairs it removed up to 41% of two-qubit gates after Qiskit
level 3. Discussed in Qiskit issue [#3829](https://github.com/Qiskit/qiskit/issues/3829).

## What's here

| Folder | Contents |
|---|---|
| `harness/` | Device targets, the predicted-error model (`damage.py`), equivalence checking (`verify.py`) |
| `scoring/` | Is an output runnable on the device; metrics; small-circuit checks; IBM access |
| `frontier/` | `run_frontier.py` (compare compilers on circuits), `random_check.py` (random-input correctness check), `hardware_frontier.py` (real-chip test), `compile_ai_live.py` (AI transpiler on a saved live calibration) |
| `toffoli/` | The relative-phase Toffoli pass |
| `results/` | Reports, compiled circuits (QPY) for every compiler, sources, hardware results |

## Reproduce or test your own compiler

```
pip install -r requirements.txt
# compare any compiler (a .py file with compile(circuit, target, seed) -> circuit) against Qiskit
python frontier/run_frontier.py path/to/circuits --program path/to/your_compiler.py --target fake:FakeKingston --qiskit-seeds 32
# check saved outputs on random inputs
python frontier/random_check.py frontier/results/<run> --trials 3
```

IBM's AI transpiler (`qiskit-ibm-transpiler`) needs a recent PyTorch; it installs on Linux (I used
Google Colab). Hardware runs need an IBM Quantum account; the free plan's 10 minutes a month were
enough (each run above used under 10 seconds).

## Limits

- Two circuit types on hardware (eight runs, three chips); not peer-reviewed.
- Predicted error comes from my own model; it ranked pairs of compilations correctly about 80% of the time
  in earlier hardware tests.
- The compiler is slow (about 2 minutes per 64-qubit circuit) and does not scale to 100+ qubit circuits yet.

## Credits

Circuits: Quantum Advantage Tracker contributors, in particular the Anderson impurity model submission
(IBM, Oak Ridge National Laboratory, University of Maryland). Tools: Qiskit, qiskit-ibm-transpiler,
qiskit-aer, MQT QCEC. AI tools were used in building the compiler and this harness.

## Licence

Apache-2.0 for the code in this repository. Circuits from the tracker keep their original licence.
