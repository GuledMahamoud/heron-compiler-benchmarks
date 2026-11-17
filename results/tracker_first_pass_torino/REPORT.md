# Frontier test — 2026-11-16 19:14

Target `fake:FakeTorino`; programs: ours.py; Qiskit best of 8 seeds; program seeds 1; limit 1800 s.  Level 1 = verified, and at least 10% fewer two-qubit gates than the best of Qiskit, the AI transpiler and the circuit as published.

## floquet_mixed_field_ising_mag_51qx16c.qasm (51 qubits, 896 two-qubit gates in the source)

| compiler | status | 2q gates | 2q depth | duration (ns) | predicted damage | seconds | check |
|---|---|---:|---:|---:|---:|---:|---|
| qiskit | off_target | – | – | – | – | 7.0 | uses qubits or couplers the calibration marks unusable (error >= 0.5): coupler 57-58, coupler 58-59 |
| ours s0 | off_target | – | – | – | – | 111.2 | uses qubits or couplers the calibration marks unusable (error >= 0.5): coupler 74-86, coupler 85-86, qubit 85, qubit 86, |

**no verified comparison**

## peaked_circuit_P9_Hqap_56x1917.qasm (56 qubits, 1917 two-qubit gates in the source)

| compiler | status | 2q gates | 2q depth | duration (ns) | predicted damage | seconds | check |
|---|---|---:|---:|---:|---:|---:|---|
| qiskit | off_target | – | – | – | – | 35.9 | uses qubits or couplers the calibration marks unusable (error >= 0.5): coupler 21-34 |
| ours s0 | off_target | – | – | – | – | 114.5 | uses qubits or couplers the calibration marks unusable (error >= 0.5): coupler 21-34 |

**no verified comparison**

## nq70_depth70_checks27_basis_fstate.qasm (70 qubits, 2415 two-qubit gates in the source)

| compiler | status | 2q gates | 2q depth | duration (ns) | predicted damage | seconds | check |
|---|---|---:|---:|---:|---:|---:|---|
| qiskit | proven | 2415 | 70 | 11544 | 16.043 | 5.0 | qcec equivalent_up_to_global_phase |
| ours s0 | proven | 2415 | 70 | 10424 | 15.509 | 115.2 | qcec equivalent |

**not better: ours s0 2415 two-qubit gates vs 2415 (+0%)**

## 49Q_OLE_circuit_L_3_b_0.25_delta0.15.qasm (49 qubits, 648 two-qubit gates in the source)

_reduced from 156 to its 49 active qubits_

| compiler | status | 2q gates | 2q depth | duration (ns) | predicted damage | seconds | check |
|---|---|---:|---:|---:|---:|---:|---|
| qiskit | unverified | 390 | 32 | 5168 | 4.388 | 1.4 | undecided in 120 s (timeout); no statevector check above 20 qubits |
| ours s0 | unverified | 390 | 32 | 4864 | 4.379 | 108.1 | undecided in 120 s (timeout); no statevector check above 20 qubits |

**no verified comparison**

