# Testing a quantum compiler on frontier circuits and IBM hardware

This repository holds the test harness, the results and one compiler pass from an independent project:
a compiler for IBM quantum chips, tested against Qiskit and IBM's AI transpiler on circuits from
published quantum research, and on IBM's real hardware.

The compiler itself was found with an AI-assisted search that I run privately; its source is not
included. Everything needed to **check** the results is: every compiled circuit, the circuits they came
from, the scripts that scored and verified them, and the hardware job results.

*Status: work in progress, November 2026. Not peer-reviewed. Numbers below are what I measured, with
their limits.*

## Results in short

**Circuits.** From the [Quantum Advantage Tracker](https://quantum-advantage-tracker.github.io/), mainly
the Anderson impurity model Trotter circuits (64 qubits) from the IBM / Oak Ridge National Laboratory /
University of Maryland submission. All comparisons use the same simulated or live calibration for every
compiler, with broken couplers and qubits removed for all of them.

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
time. Score = share of shots in the right sector; two compilations per compiler per run.

| Run | Chip | This compiler | Qiskit | IBM AI transpiler |
|---|---|---|---|---|
| 1 | ibm_fez | 4.18%, 3.93% | 3.55%, 1.85% | – |
| 2 | ibm_marrakesh | 4.65%, 2.59% | 2.17%, 3.44% | – |
| 3 | ibm_fez | 3.44%, 3.05% | 3.44%, 2.43% | 1.65%, 3.05% |

Averaged over the three runs, this compiler kept about **1.3×** as many in-sector shots as Qiskit
(3.6% vs 2.8%), and won 9 of 12 head-to-head comparisons (1 tie). Against the AI transpiler (run 3 only)
about 1.4×. The signal is small (everything is close to the 2% random level), runs vary, and this is one
circuit, so treat it as **early evidence**, not a settled result. trotter-3 on hardware was
indistinguishable from random for every compiler.

**Correctness.** Every compiled circuit that ran on hardware was checked against the original on random
input states with a matrix-product-state simulator: all scored 1.000000 (exact match to simulator
precision). A deliberately broken copy (one two-qubit gate removed) scored far lower (averages 0.10 and 0.35
over two tests; individual inputs 0.01 to 0.98), so the check does catch errors. Smaller outputs are proven equivalent with
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

- One main circuit family on hardware; small effects; not peer-reviewed.
- Predicted error comes from my own model; it ranked pairs of compilations correctly about 80% of the time
  in earlier hardware tests.
- The compiler is slow (about 2 minutes per 64-qubit circuit) and does not scale to 100+ qubit circuits yet.

## Credits

Circuits: Quantum Advantage Tracker contributors, in particular the Anderson impurity model submission
(IBM, Oak Ridge National Laboratory, University of Maryland). Tools: Qiskit, qiskit-ibm-transpiler,
qiskit-aer, MQT QCEC. AI tools were used in building the compiler and this harness.

## Licence

Apache-2.0 for the code in this repository. Circuits from the tracker keep their original licence.
