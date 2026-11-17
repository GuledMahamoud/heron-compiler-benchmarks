"""Frontier-circuit test: a compiler under test against Qiskit and IBM's AI transpiler on outside circuits.

    cd ~/quantum-compiler
    nice -n 19 .venv/bin/python frontier/run_frontier.py frontier/circuits \
        --program path/to/your_compiler.py --target fake:FakeTorino

Reads every .qasm (OpenQASM 2 or 3) and .qpy file in the circuits folder, smallest first, and for each:

  theirs    the circuit as supplied, if it already runs on the target (an "ISA" circuit)
  qiskit    Qiskit level 3, best of --qiskit-seeds seeds by the v3 cost
  ai        qiskit-ibm-transpiler's generate_ai_pass_manager (skipped, with a note, if not installed)
  program   the --program file(s), seeds 0..--program-seeds-1, each in a child process with a time limit

Every output is checked for conformance (native gates, coupled pairs, no dead hardware:
scoring.conformance) and for equivalence with the source (harness.verify: qcec, then the
exact / random-state checks of scoring.checks for small outputs; plus a Clifford tableau check for
Clifford circuits, which works at any size).  Metrics and the v3 cost are scoring.metrics', so the
numbers mean the same thing for every compiler.

Outputs go to frontier/results/<timestamp>/.  No IBM hardware time is used.  The program file is copied
into the run folder first, so editing it does not affect a test in progress.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LEVEL1 = 0.90  # "10% or more better than both": program 2q gates <= 0.9 x the better of qiskit / ai


# ----------------------------------------------------------------------------- loading
def load_circuit(path: Path):
    from qiskit import qasm2, qpy
    from harness import benchmarks as B
    if path.suffix == ".qpy" or path.name.endswith(".qpy.gz"):
        opener = gzip.open if path.name.endswith(".gz") else open
        with opener(path, "rb") as f:
            qc = qpy.load(f)[0]
    else:
        text = path.read_text(errors="replace")
        if "OPENQASM 3" in text:
            from qiskit import qasm3
            qc = qasm3.loads(text)  # needs qiskit_qasm3_import
        else:
            qc = qasm2.loads(text, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    if qc.parameters:
        raise ValueError(f"circuit has {len(qc.parameters)} unbound parameters; bind them before testing")
    qc.name = path.stem.replace(".qpy", "")
    return B.prepare(qc)  # strip barriers and final measurements, as for every benchmark


def to_logical(qc):
    """A supplied circuit that is already laid out on a device (has a layout, or is as wide as the
    device) is compiled from its active qubits only, so every compiler starts from the same logical
    circuit.  Returns (logical circuit, note)."""
    from qiskit import QuantumCircuit
    used = sorted({qc.find_bit(q).index for inst in qc.data for q in inst.qubits})
    if len(used) == qc.num_qubits:
        return qc, ""
    pos = {p: i for i, p in enumerate(used)}
    out = QuantumCircuit(len(used), name=qc.name)
    for inst in qc.data:
        out.append(inst.operation, [pos[qc.find_bit(q).index] for q in inst.qubits])
    return out, f"reduced from {qc.num_qubits} to its {len(used)} active qubits"



# ----------------------------------------------------------------------------- dead hardware
def avoid_dead(target, keep_connected: bool = False):
    """(copy of `target` without two-qubit gates on dead couplers or touching dead qubits, number removed,
    dead qubits).  Device Targets keep broken couplers (error 1.0) as usable, and circuits shaped to fill
    the heavy-hex lattice get routed through them by every compiler.  Compiling on this copy makes the
    outputs pass the same dead-hardware rule for every compiler; they are still scored and checked
    on the full target."""
    from qiskit.transpiler import Target
    from harness.damage import DEAD, MIN_T1, from_target
    cal = from_target(target, "frontier")
    bad_q = {int(q) for q, p in cal.qubit.items() if p["sx_error"] >= DEAD or p["t1"] < MIN_T1 or p["readout_error"] >= DEAD}

    def usable(qs):
        if qs is None or len(qs) != 2:
            return True
        a, b = qs
        c = cal.coupler.get(cal.edge(a, b))
        return a not in bad_q and b not in bad_q and c is not None and c["error"] < DEAD

    drop = None  # undirected couplers to drop; None = drop every unusable one
    if keep_connected:
        # keep an unusable coupler when dropping it would cut qubits off: IBM's AI router (Sabre layout
        # inside) panics on a disconnected coupling map.  Its output still faces the dead-hardware check.
        import rustworkx as rx
        g = target.build_coupling_map().graph.to_undirected(multigraph=False)
        bad = sorted({tuple(sorted(e)) for e in g.edge_list() if not usable(e)})
        drop = set()
        for e in bad:
            g2 = g.copy(); g2.remove_edge(*e)
            if rx.is_connected(g2):
                g = g2; drop.add(e)

    def dropped(qs):
        if qs is None or len(qs) != 2:
            return False
        return (not usable(qs)) if drop is None else tuple(sorted(qs)) in drop

    new = Target(num_qubits=target.num_qubits, dt=target.dt, qubit_properties=target.qubit_properties)
    removed = 0
    for op in target.operation_names:
        props = target[op]
        if props is None or set(props) == {None}:
            new.add_instruction(target.operation_from_name(op), name=op)
            continue
        if target.operation_from_name(op).num_qubits == 2:
            keep = {q: p for q, p in props.items() if not dropped(q)}
            removed += len(props) - len(keep)
            props = keep
        new.add_instruction(target.operation_from_name(op), dict(props), name=op)
    return new, removed, sorted(bad_q)

# ----------------------------------------------------------------------------- compilers
def compile_qiskit(src, target, seeds: int):
    from qiskit.transpiler import generate_preset_pass_manager
    from scoring.metrics import cost, metrics
    best = None
    for s in range(seeds):
        out = generate_preset_pass_manager(optimization_level=3, target=target, seed_transpiler=s).run(src)
        c = cost(metrics(out, target), "v3")
        if best is None or c < best[0]:
            best = (c, s, out)
    return best[2], {"seed": best[1]}


def compile_ai(src, target, spec: str, ctarget=None):
    """IBM's AI passes, run locally, given the fake backend (so the output is in its native gates).  The
    backend's Target is swapped for `ctarget` (broken couplers removed) when one is given, so the AI
    router avoids the same dead hardware as the other compilers."""
    from qiskit_ibm_transpiler import generate_ai_pass_manager
    kw = dict(optimization_level=3, ai_optimization_level=3)
    kind, _, arg = spec.partition(":")
    note = {}
    if kind == "fake":
        from qiskit_ibm_runtime import fake_provider as fp
        backend = getattr(fp, arg.partition("@")[0])()
        if ctarget is not None:
            try:
                backend._target = ctarget
                note["dead_avoided"] = backend.target is ctarget
            except Exception:  # noqa: BLE001
                note["dead_avoided"] = False
        kw["backend"] = backend
    else:
        kw["coupling_map"] = (ctarget or target).build_coupling_map()
    return generate_ai_pass_manager(**kw).run(src), note


def run_program(program: Path, src_path: Path, spec: str, seed: int, limit: float):
    """(circuit | None, error | None, seconds): the program in a child process with a time limit."""
    from qiskit import qpy
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "out.qpy"
        p = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--child", str(program), str(src_path), spec, str(seed), str(out)],
                             cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            _, err = p.communicate(timeout=limit)
        except subprocess.TimeoutExpired:
            p.kill(); p.communicate()
            return None, f"timeout after {limit:.0f} s", time.perf_counter() - t0
        dt = time.perf_counter() - t0
        if p.returncode != 0 or not out.exists():
            return None, "crashed: " + " | ".join(err.decode(errors="replace").strip().splitlines()[-4:])[:600], dt
        with open(out, "rb") as f:
            return qpy.load(f)[0], None, dt


def child(program: str, src_path: str, spec: str, seed: str, out_path: str) -> int:
    import importlib.util
    import traceback
    from qiskit import qpy
    from harness.compile import target_for
    try:
        with open(src_path, "rb") as f:
            qc = qpy.load(f)[0]
        ms = importlib.util.spec_from_file_location("compiler_under_test", program)
        mod = importlib.util.module_from_spec(ms)
        ms.loader.exec_module(mod)
        target = target_for(spec)
        if os.environ.get("FRONTIER_ALLOW_DEAD") != "1":
            target = avoid_dead(target)[0]
        out = mod.compile(qc, target, int(seed))
        with open(out_path, "wb") as f:
            qpy.dump(out, f)
    except BaseException:  # noqa: BLE001
        traceback.print_exc(limit=6)
        return 3
    return 0


# ----------------------------------------------------------------------------- checks
def clifford_check(src, out) -> str | None:
    """Equal Clifford tableaux of the source (at the initial layout, then the routing permutation) and
    the output: a proof at any size.  None when either is not Clifford.  Unequal is 'inconclusive':
    the output may still be correct on the inputs whose ancillas are |0>."""
    from qiskit.quantum_info import Clifford
    from harness.verify import explicit_reference
    ref, nolayout = explicit_reference(src, out)
    if ref is None:
        return None
    try:
        a, b = Clifford(ref), Clifford(nolayout)
    except Exception:  # noqa: BLE001 - not a Clifford circuit
        return None
    return "proven (Clifford tableau)" if a == b else "inconclusive (Clifford tableaux differ)"


def check(src, out, timeout: float) -> tuple[str, str]:
    """(status, how): status is proven | probable | refuted | unverified."""
    cl = clifford_check(src, out)
    if cl and cl.startswith("proven"):
        return "proven", cl
    from harness.verify import REFUTED, verify
    v = verify(src, out, timeout=timeout)
    if v["passed"]:
        return "proven", f"qcec {v['status']}"
    if v["probable"]:
        return "probable", "qcec random-basis simulations agree"
    if v["status"] in REFUTED:
        return "refuted", f"qcec {v['status']}"
    how = "no statevector check above 20 qubits"
    if src.num_qubits <= 20:  # dense checks are 2^n: never attempt them on frontier-size circuits
        try:
            from scoring.checks import exact_check, state_check
            ex = exact_check(src, out)
            if ex is not None and ex.get("status") in ("equivalent", "equivalent_up_to_global_phase"):
                return "proven", f"exact operator check (infidelity {ex['process_infidelity']:.1e})"
            if ex is not None and ex.get("status") == "not_equivalent":
                return "refuted", "exact operator check: not equivalent"
            sc = state_check(src, out)
            if sc.get("status") == "states_agree":
                return "probable", f"random-state check (worst infidelity {sc.get('worst_infidelity', float('nan')):.1e})"
            how = f"random-state check: {sc.get('status')}"
        except Exception as e:  # noqa: BLE001
            how = f"fallback check failed: {type(e).__name__}"
    return "unverified", f"undecided in {timeout:.0f} s ({v['status']}); {how}" + (f"; {cl}" if cl else "")


def score(label: str, out, src, target, timeout: float, extra: dict, verify_it: bool = True) -> dict:
    from scoring.conformance import conformance
    from scoring.metrics import cost, metrics
    rec = {"compiler": label, **extra}
    why = conformance(out, target)
    if why:
        return {**rec, "status": "off_target", "error": why}
    m = metrics(out, target)
    status, how = check(src, out, timeout) if verify_it else ("supplied", "the circuit as published; not re-checked")
    return {**rec, **m, "v3_cost": cost(m, "v3"), "status": status, "verify": how}


# ----------------------------------------------------------------------------- driver
def test_one(path: Path, a, programs: list[Path], run_dir: Path, log) -> dict:
    from qiskit import qpy
    from harness.compile import target_for
    target = target_for(a.target)
    ctarget = target if a.allow_dead else avoid_dead(target)[0]  # compile here, score on `target`
    raw = load_circuit(path)
    src, note = to_logical(raw)
    res = {"circuit": path.name, "qubits": src.num_qubits, "source_2q": sum(1 for i in src.data if i.operation.num_qubits == 2),
           "note": note, "rows": []}
    if src.num_qubits > target.num_qubits:
        res["skip"] = f"{src.num_qubits} qubits > target's {target.num_qubits}"
        return res
    src_path = run_dir / "sources" / f"{path.stem}.qpy"
    src_path.parent.mkdir(exist_ok=True)
    with open(src_path, "wb") as f:
        qpy.dump(src, f)

    def add(rec, circ=None):
        res["rows"].append(rec)
        log(f"  {rec['compiler']:<14} {rec.get('status', ''):<11} 2q={rec.get('two_qubit', '-')}  "
            f"depth2q={rec.get('depth_2q', '-')}  damage={rec.get('damage', float('nan')):.3f}  {rec.get('error', rec.get('verify', ''))[:90]}")
        if circ is not None:
            d = run_dir / "compiled"; d.mkdir(exist_ok=True)
            with gzip.open(d / f"{path.stem}__{rec['compiler'].replace(' ', '_')}.qpy.gz", "wb") as f:
                qpy.dump(circ, f)

    # theirs: only when the supplied circuit already runs on this target as it is
    if raw.num_qubits == target.num_qubits and raw.layout is not None:
        add(score("theirs", raw, src, target, a.verify_timeout, {}, verify_it=False), raw)

    t0 = time.perf_counter()
    try:
        out, ex = compile_qiskit(src, ctarget, a.qiskit_seeds)
        add(score("qiskit", out, src, target, a.verify_timeout, {**ex, "seconds": round(time.perf_counter() - t0, 1)}), out)
    except Exception as e:  # noqa: BLE001
        add({"compiler": "qiskit", "status": "error", "error": f"{type(e).__name__}: {e}"[:300]})

    if not a.no_ai:
        t0 = time.perf_counter()
        try:
            out, ex = compile_ai(src, target, a.target, None if a.allow_dead else avoid_dead(target, keep_connected=True)[0])
            add(score("ai", out, src, target, a.verify_timeout, {**ex, "seconds": round(time.perf_counter() - t0, 1)}), out)
        except ImportError as e:
            add({"compiler": "ai", "status": "not_installed", "error": f"{e} (pip install 'qiskit-ibm-transpiler[ai-local-mode]')"})
        except Exception as e:  # noqa: BLE001
            add({"compiler": "ai", "status": "error", "error": f"{type(e).__name__}: {e}"[:300]})

    for prog in programs:
        for s in range(a.program_seeds):
            out, err, dt = run_program(prog, src_path, a.target, s, a.limit)
            label = f"{prog.stem} s{s}"
            if out is None:
                add({"compiler": label, "status": "error", "error": err, "seconds": round(dt, 1)})
            else:
                add(score(label, out, src, target, a.verify_timeout, {"seconds": round(dt, 1)}), out)
    return res


def verdict(res: dict) -> str:
    ok = {"proven", "probable", "supplied"}
    rows = [r for r in res["rows"] if r.get("status") in ok]
    ref = [r["two_qubit"] for r in rows if r["compiler"] in ("qiskit", "ai", "theirs")]
    prog = [r for r in rows if r["compiler"] not in ("qiskit", "ai", "theirs")]
    if not ref or not prog:
        return "no verified comparison"
    best = min(prog, key=lambda r: r["v3_cost"])
    r2 = (best["two_qubit"] + 1) / (min(ref) + 1)
    tag = "LEVEL 1" if r2 <= LEVEL1 else ("better" if r2 < 1 else "not better")
    return f"{tag}: {best['compiler']} {best['two_qubit']} two-qubit gates vs {min(ref)} ({(1 - r2) * 100:+.0f}%)"


def report(results: list[dict], a, run_dir: Path) -> None:
    L = [f"# Frontier test — {datetime.now():%Y-%m-%d %H:%M}", "",
         f"Target `{a.target}`; programs: {', '.join(Path(p).name for p in a.program)}; Qiskit best of {a.qiskit_seeds} seeds; "
         f"program seeds {a.program_seeds}; limit {a.limit:.0f} s.  Level 1 = verified, and at least 10% fewer two-qubit "
         "gates than the best of Qiskit, the AI transpiler and the circuit as published.", ""]
    for res in results:
        L += [f"## {res['circuit']} ({res['qubits']} qubits, {res['source_2q']} two-qubit gates in the source)", ""]
        if res.get("note"):
            L.append(f"_{res['note']}_\n")
        if res.get("skip") or res.get("error"):
            L += [f"Skipped: {res.get('skip') or res.get('error')}", ""]
            continue
        L += ["| compiler | status | 2q gates | 2q depth | duration (ns) | predicted damage | seconds | check |", "|---|---|---:|---:|---:|---:|---:|---|"]
        for r in res["rows"]:
            f = lambda k, fmt="{}": fmt.format(r[k]) if k in r else "–"  # noqa: E731
            L.append(f"| {r['compiler']} | {r.get('status', '')} | {f('two_qubit')} | {f('depth_2q')} | {f('duration_ns', '{:.0f}')} | "
                     f"{f('damage', '{:.3f}')} | {f('seconds')} | {(r.get('verify') or r.get('error') or '')[:120]} |")
        L += ["", f"**{verdict(res)}**", ""]
    (run_dir / "REPORT.md").write_text("\n".join(L) + "\n")


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        return child(*sys.argv[2:7])
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("circuits", type=Path, help="folder of .qasm / .qpy circuits")
    ap.add_argument("--program", action="append", required=True, help="compiler file defining compile(circuit, target, seed); repeat to test several")
    ap.add_argument("--target", default="fake:FakeTorino")
    ap.add_argument("--qiskit-seeds", type=int, default=8, help="32 is slow at 100+ qubits")
    ap.add_argument("--program-seeds", type=int, default=1)
    ap.add_argument("--limit", type=float, default=1800.0, help="seconds per program compile")
    ap.add_argument("--verify-timeout", type=float, default=120.0)
    ap.add_argument("--max-qubits", type=int, default=None, help="skip circuits wider than this")
    ap.add_argument("--only", default=None, help="only circuits whose file name contains this text")
    ap.add_argument("--no-ai", action="store_true")
    ap.add_argument("--allow-dead", action="store_true", help="compile on the full target, broken couplers included")
    a = ap.parse_args()
    if a.allow_dead:
        os.environ["FRONTIER_ALLOW_DEAD"] = "1"  # children inherit it
    else:
        from harness.compile import target_for
        _, n, bq = avoid_dead(target_for(a.target))
        print(f"compiling without {n} two-qubit gate entries on dead couplers or dead qubits ({len(bq)} dead qubits)")
    try:
        os.nice(19)  # lowest priority: never slow anything else down
    except OSError:
        pass

    run_dir = ROOT / "frontier" / "results" / datetime.now().strftime("%Y%m%d-%H%M%S")
    (run_dir / "programs").mkdir(parents=True)
    programs = []
    for p in a.program:
        dst = run_dir / "programs" / Path(p).name
        shutil.copy2(ROOT / p if not Path(p).is_absolute() else p, dst)  # frozen copy
        programs.append(dst)

    files = sorted([p for p in a.circuits.iterdir() if p.suffix in (".qasm", ".qpy") or p.name.endswith(".qpy.gz")])
    if a.only:
        files = [p for p in files if a.only in p.name]
    sized = []
    for p in files:
        try:
            sized.append((load_circuit(p).num_qubits, p))
        except Exception as e:  # noqa: BLE001
            print(f"cannot load {p.name}: {type(e).__name__}: {e}"[:300])
    sized.sort()
    logf = open(run_dir / "run.log", "a")

    def log(msg):
        print(msg, flush=True)
        logf.write(msg + "\n"); logf.flush()

    results = []
    for n, p in sized:
        if a.max_qubits and n > a.max_qubits:
            log(f"skip {p.name}: {n} qubits > --max-qubits {a.max_qubits}")
            continue
        log(f"{p.name} ({n} qubits)")
        try:
            res = test_one(p, a, programs, run_dir, log)
        except Exception as e:  # noqa: BLE001
            res = {"circuit": p.name, "qubits": n, "source_2q": 0, "rows": [], "error": f"{type(e).__name__}: {e}"[:300]}
            log(f"  failed: {res['error']}")
        if res.get("rows"):
            log(f"  -> {verdict(res)}")
        results.append(res)
        (run_dir / "results.json").write_text(json.dumps(results, indent=1, default=str))
        report(results, a, run_dir)
    log(f"done: {run_dir.relative_to(ROOT)}/REPORT.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
