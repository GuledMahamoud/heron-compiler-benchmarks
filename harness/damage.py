"""Damage model v0: the error a compiled circuit is predicted to accumulate on a specific chip.

    damage = Σ_gates ε(gate on these physical qubits)                      -- cz per coupler, sx/x per qubit, rz free
           + Σ_logical qubits ε_idle(time it waits; T1, T2 of its qubit)   -- (3 − e^{−t/T1} − 2e^{−t/T2}) / 6
           + Σ_logical qubits ε_readout(its final physical qubit)
    predicted fidelity ≈ exp(−damage)                                      -- Π(1 − εᵢ) to first order

Damage adds, fidelity multiplies: optimise the sum, report the product (brief §3).

The calibration is a table keyed by physical qubit and coupler.  `synthetic_from_fake_backend`
fills it for the 57-qubit heavy-hex lattice by sampling, with a fixed seed, the per-gate values of a
real IBM Heron calibration snapshot (qiskit-ibm-runtime's FakeTorino: 133 qubits, cz basis).  No IBM
device has Qiskit's heavy_hex(5) as a subgraph (checked against every ≥57-qubit fake backend), so the
*placement* is synthetic; the *distribution* is real.  Per-qubit values are sampled as a tuple from
one real qubit, so sx error, readout error, T1 and T2 keep their correlations.  Dead couplers and
qubits (error ≥ 0.5) are left out of the pool because a real device's compiler would route around them.

Idle model v0: each logical qubit is treated as sitting on its final physical qubit for the whole
circuit; its idle time is the schedule length minus that qubit's busy time.  Qubits that only carry
data transiently (SWAP relays) are ignored, and a qubit in |0> does not decay, so this is a lower bound
on idle damage.  Schedule: ASAP list scheduling over the gate order with the calibrated durations.
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

from qiskit.circuit import ControlFlowOp

from .benchmarks import ROOT
from .target import heavy_hex_coupling_map

DEAD = 0.5          # an error rate at or above this means "unusable", not "noisy"
MIN_T1 = 10e-6      # seconds; below this the qubit is dead in the snapshot


@dataclass
class Calibration:
    source: str
    num_qubits: int
    coupler: dict[str, dict]          # "p-q" (p<q) -> {"error", "duration"}
    qubit: dict[str, dict]            # "p" -> {"sx_error", "x_error", "sx_duration", "readout_error", "readout_duration", "t1", "t2"}
    rz_duration: float = 0.0
    notes: str = ""
    stats: dict = field(default_factory=dict)

    @staticmethod
    def edge(p: int, q: int) -> str:
        return f"{min(p, q)}-{max(p, q)}"

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=1))

    @classmethod
    def load(cls, path: Path) -> "Calibration":
        return cls(**json.loads(path.read_text()))


def _rng_summary(xs):
    xs = sorted(xs)
    return {"min": xs[0], "median": xs[len(xs) // 2], "max": xs[-1], "n": len(xs)}


def synthetic_from_fake_backend(backend_name: str = "FakeTorino", distance: int = 5, seed: int = 0) -> Calibration:
    from qiskit_ibm_runtime import fake_provider as fp
    be = getattr(fp, backend_name)()
    T = be.target
    live_qubits = []
    for q in range(T.num_qubits):
        sx = T["sx"].get((q,)); x = T["x"].get((q,)); me = T["measure"].get((q,)); qp = T.qubit_properties[q]
        if None in (sx, x, me) or sx.error is None or me.error is None or qp.t1 is None or qp.t2 is None:
            continue
        if sx.error >= DEAD or me.error >= DEAD or qp.t1 < MIN_T1:
            continue
        live_qubits.append({"sx_error": sx.error, "x_error": x.error if x.error is not None else sx.error,
                            "sx_duration": sx.duration, "readout_error": me.error, "readout_duration": me.duration,
                            "t1": qp.t1, "t2": qp.t2})
    two_q = next(op for op in ("cz", "ecr", "cx") if op in T.operation_names)
    live_edges = [{"error": p.error, "duration": p.duration} for qs, p in T[two_q].items()
                  if p is not None and p.error is not None and p.error < DEAD]
    rng = random.Random(seed)
    cm = heavy_hex_coupling_map(distance)
    edges = sorted({Calibration.edge(a, b) for a, b in cm.get_edges()})
    if len(live_qubits) < cm.size() or len(live_edges) < len(edges):
        raise ValueError("snapshot has fewer live qubits/couplers than the lattice needs")
    qsample = rng.sample(live_qubits, cm.size())
    esample = rng.sample(live_edges, len(edges))
    cal = Calibration(
        source=f"{be.name} snapshot (qiskit-ibm-runtime fake provider), {two_q} basis, sampled with seed {seed}",
        num_qubits=cm.size(),
        coupler={e: dict(v) for e, v in zip(edges, esample)},
        qubit={str(q): dict(v) for q, v in enumerate(qsample)},
        rz_duration=0.0,
        notes=f"synthetic placement onto heavy_hex({distance}); dead qubits/couplers (error >= {DEAD}, T1 < {MIN_T1}) excluded; "
              f"{len(live_qubits)} live qubits and {len(live_edges)} live couplers in the pool",
    )
    cal.stats = {
        "two_qubit_error": _rng_summary([v["error"] for v in cal.coupler.values()]),
        "sx_error": _rng_summary([v["sx_error"] for v in cal.qubit.values()]),
        "readout_error": _rng_summary([v["readout_error"] for v in cal.qubit.values()]),
        "t1_us": _rng_summary([v["t1"] * 1e6 for v in cal.qubit.values()]),
        "t2_us": _rng_summary([v["t2"] * 1e6 for v in cal.qubit.values()]),
        "two_qubit_duration_ns": _rng_summary([v["duration"] * 1e9 for v in cal.coupler.values()]),
    }
    return cal


def idle_error(t: float, t1: float, t2: float) -> float:
    """Average infidelity of thermal relaxation for time t (exact for the T1/T2 channel, 0 at t=0, 1/2 at t→∞)."""
    return (3.0 - math.exp(-t / t1) - 2.0 * math.exp(-t / t2)) / 6.0


DEFAULT_WEIGHTS = {"two_qubit": 1.0, "one_qubit": 1.0, "mid_measure": 1.0, "idle": 1.0, "readout": 1.0}


def damage(circuit, cal: Calibration, weights: dict | None = None) -> dict:
    """Predicted damage of a compiled circuit whose qubits are the lattice's physical qubits.
    `weights` multiplies each term (fitted to hardware in earlier hardware tests; 1.0 = calibration at face value)."""
    n = circuit.num_qubits
    ready = [0.0] * n
    busy = [0.0] * n
    acc = {"two_qubit": 0.0, "one_qubit": 0.0, "mid_measure": 0.0, "idle": 0.0, "readout": 0.0}
    counts = {"two_qubit": 0, "one_qubit": 0}

    def gate(name: str, qs: list[int]) -> tuple[float, float]:
        """(error, duration) of one native operation on physical qubits qs."""
        if name in ("cz", "ecr", "cx"):
            c = cal.coupler.get(Calibration.edge(*qs))
            if c is None:
                raise KeyError(f"cz on {qs} is not a coupler of the lattice")
            counts["two_qubit"] += 1
            acc["two_qubit"] += c["error"]
            return c["error"], c["duration"]
        q = cal.qubit[str(qs[0])]
        if name in ("sx", "x"):
            counts["one_qubit"] += 1
            e = q["sx_error"] if name == "sx" else q["x_error"]
            acc["one_qubit"] += e
            return e, q["sx_duration"]
        if name == "rz":
            return 0.0, cal.rz_duration
        if name in ("measure", "reset"):
            acc["mid_measure"] += q["readout_error"]
            return q["readout_error"], q["readout_duration"]
        if name in ("barrier", "delay", "id"):
            return 0.0, 0.0
        raise KeyError(f"no calibration for gate {name!r}")

    def walk(insts, qubit_of):
        for inst in insts:
            qs = [qubit_of(q) for q in inst.qubits]
            op = inst.operation
            if isinstance(op, ControlFlowOp):
                # branches are counted as if every block runs: an upper bound on gate error, max on time
                t_before = [ready[q] for q in qs]
                t_end = max(t_before) if t_before else 0.0
                for block in op.blocks:
                    for q, t in zip(qs, t_before):
                        ready[q] = t
                    inner = {bq: pq for bq, pq in zip(block.qubits, qs)}
                    walk(block.data, lambda b, inner=inner: inner[b])
                    t_end = max([t_end] + [ready[q] for q in qs])
                for q in qs:
                    ready[q] = t_end
                continue
            _, d = gate(op.name, qs)
            start = max((ready[q] for q in qs), default=0.0)
            for q in qs:
                ready[q] = start + d
                busy[q] += d

    walk(circuit.data, lambda q: circuit.find_bit(q).index)
    total_time = max(ready) if ready else 0.0
    final = (circuit.layout.final_index_layout(filter_ancillas=True) if circuit.layout is not None
             else list(range(n)))
    for p in final:
        q = cal.qubit[str(p)]
        acc["idle"] += idle_error(max(0.0, total_time - busy[p]), q["t1"], q["t2"])
        acc["readout"] += q["readout_error"]
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    total = sum(w[k] * v for k, v in acc.items())
    return {"total": total, "fidelity": math.exp(-total), "duration_us": total_time * 1e6, "weights": w,
            **{k: v for k, v in acc.items()}, "n_two_qubit": counts["two_qubit"], "n_one_qubit": counts["one_qubit"]}


def from_fake_backend(backend_name: str = "FakeTorino") -> Calibration:
    from qiskit_ibm_runtime import fake_provider as fp
    be = getattr(fp, backend_name)()
    return from_target(be.target, f"{be.name} snapshot (qiskit-ibm-runtime fake provider)")


def from_target(T, source: str) -> Calibration:
    """A Target's own values on its own qubits: real placement, no sampling.  Dead couplers and qubits
    keep their values (the compiler sees them in the Target and may still use them)."""
    two_q = next(op for op in ("cz", "ecr", "cx") if op in T.operation_names)
    qubit = {}
    for q in range(T.num_qubits):
        sx = T["sx"].get((q,)); x = T["x"].get((q,)); me = T["measure"].get((q,)); qp = T.qubit_properties[q]
        qubit[str(q)] = {"sx_error": sx.error or 0.0, "x_error": (x.error if x and x.error is not None else sx.error) or 0.0,
                         "sx_duration": sx.duration or 0.0, "readout_error": me.error or 0.0, "readout_duration": me.duration or 0.0,
                         "t1": qp.t1 or 1e-3, "t2": qp.t2 or 1e-3}
    coupler = {}
    for qs, p in T[two_q].items():
        if p is not None:
            e = Calibration.edge(*qs)
            if e not in coupler or (p.error or 0) > coupler[e]["error"]:
                coupler[e] = {"error": p.error or 0.0, "duration": p.duration or 0.0}
    cal = Calibration(source=f"{source}, {two_q} basis, real placement",
                      num_qubits=T.num_qubits, coupler=coupler, qubit=qubit, rz_duration=0.0,
                      notes="values on the device's own qubits; dead couplers/qubits included as the compiler sees them")
    cal.stats = {
        "two_qubit_error": _rng_summary([v["error"] for v in coupler.values()]),
        "sx_error": _rng_summary([v["sx_error"] for v in qubit.values()]),
        "readout_error": _rng_summary([v["readout_error"] for v in qubit.values()]),
        "t1_us": _rng_summary([v["t1"] * 1e6 for v in qubit.values()]),
        "t2_us": _rng_summary([v["t2"] * 1e6 for v in qubit.values()]),
        "two_qubit_duration_ns": _rng_summary([v["duration"] * 1e9 for v in coupler.values()]),
    }
    return cal


def default_calibration(path: Path, seed: int = 0, spec: str = "heavy_hex:5") -> Calibration:
    """Load the results directory's chip model, creating it from the target spec if absent."""
    if path.exists():
        return Calibration.load(path)
    kind, _, arg = spec.partition(":")
    backend = arg.partition("@")[0]   # "FakeTorino@prune=0.012" -> the device; pruning changes routing, not the calibration
    if kind == "fake":
        cal = from_fake_backend(backend)
    elif kind == "ibm":
        from .target import make_target
        cal = from_target(make_target(spec), f"{backend} live calibration {__import__('datetime').date.today()}")
    else:
        cal = synthetic_from_fake_backend(distance=int(arg or 5), seed=seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    cal.save(path)
    return cal
