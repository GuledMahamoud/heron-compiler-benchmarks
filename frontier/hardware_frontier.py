"""Real-chip test on the Anderson circuits: does program's compilation keep more samples in the right
electron sector than Qiskit's?

    # 1. compile on the chip's live calibration (no chip time used); --backend fake:FakeFez for a dry run
    nice -n 19 .venv/bin/python frontier/hardware_frontier.py prepare --backend ibm_kingston
    # 2. (optional, slow) random-input check of what was prepared
    nice -n 19 .venv/bin/python frontier/random_check.py frontier/hardware/<tag> --trials 2
    # 3. submit: one Sampler job, uses chip time
    .venv/bin/python frontier/hardware_frontier.py submit --tag <tag>
    # 4. later: fetch and score
    .venv/bin/python frontier/hardware_frontier.py collect --tag <tag>

Why this score.  The Anderson circuits put 16 electrons in spin-up qubits 0-31 and 16 in spin-down
qubits 32-63, and every later gate (xx_plus_yy within one spin block, p, cp) keeps both counts fixed:
an ideal run lands every shot in the (16, 16) sector.  Noise moves shots out of it; a uniformly random
64-bit string lands in it about 2% of the time.  The in-sector fraction is what SKQD-type methods
keep (they discard the rest), so it is the quantity the team cares about, and it needs no classical
simulation.  It is not the full fidelity: errors that keep the counts (phase errors) are invisible to it.

For each circuit, four compilations on the same live target, broken couplers removed for all:
    qiskit, qiskit_2      Qiskit level 3: the best and next-best (by the v3 cost) of --qiskit-seeds seeds
    program, program_2        the program: best and next-best of --program-seeds seeds
Two of each because where a circuit lands on the chip moves the result about as much as a few gates
do (earlier hardware tests); compare the pairs.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import math
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontier"))

OUTDIR = ROOT / "frontier" / "hardware"
DEFAULT_SOURCES = ["frontier/results/20261116-210116/sources/anderson_momentum_trotter-1.qpy",
                   "frontier/results/20261116-210116/sources/anderson_momentum_trotter-3.qpy"]
DEFAULT_PROGRAM = None  # pass --program: a .py file defining compile(circuit, target, seed)
RANDOM_SECTOR_NOTE = "a uniformly random 64-bit string is in the (16, 16) sector with probability C(32,16)^2 / 2^64, about 2%"


def _prep_flags(src):
    """For each instruction, whether it is an X that is the first operation on its qubit (state preparation).
    Order-independent: equivalent circuits may list independent gates in any order."""
    touched, flags = set(), []
    for inst in src.data:
        qs = [src.find_bit(q).index for q in inst.qubits]
        flags.append(inst.operation.name == "x" and len(qs) == 1 and qs[0] not in touched)
        touched.update(qs)
    return flags


def sector_of(src, split: int) -> tuple[int, int]:
    """(electrons in qubits < split, electrons in qubits >= split) set by the preparation X gates of `src`."""
    up = down = 0
    for inst, prep in zip(src.data, _prep_flags(src)):
        if prep:
            q = src.find_bit(inst.qubits[0]).index
            up += q < split
            down += q >= split
    return up, down


def conserves(src, split: int) -> str | None:
    """None if every gate other than the preparation X gates keeps both electron counts; otherwise the reason."""
    for inst, prep in zip(src.data, _prep_flags(src)):
        if prep:
            continue
        name = inst.operation.name
        qs = [src.find_bit(q).index for q in inst.qubits]
        if name in ("p", "rz", "cp", "cz", "s", "sdg", "t", "tdg", "z", "id", "barrier", "global_phase"):
            continue
        if name in ("xx_plus_yy", "iswap", "swap") and len(qs) == 2 and ((qs[0] < split) == (qs[1] < split)):
            continue
        return f"{name} on {qs} may change the electron counts"
    return None


def top2(cands: list[tuple[float, str, object, dict]]):
    """Best and next-best by cost, the second with a different two-qubit count if one exists."""
    cands = sorted(cands, key=lambda c: c[0])
    if not cands:
        return []
    best = cands[0]
    rest = [c for c in cands[1:] if c[3]["two_qubit"] != best[3]["two_qubit"]] or cands[1:]
    return [best] + rest[:1]


def prepare(a) -> int:
    from qiskit import qpy
    import run_frontier as RF
    from scoring.conformance import conformance
    from scoring.metrics import cost, metrics
    from harness.compile import target_for

    spec = a.backend if a.backend.startswith("fake:") else f"ibm:{a.backend}"
    tag = a.tag or f"{a.backend.replace('fake:', 'dryrun_')}_{dt.datetime.now():%Y%m%d-%H%M}"
    out = OUTDIR / tag
    for d in ("sources", "compiled", "programs"):
        (out / d).mkdir(parents=True, exist_ok=True)
    prog = out / "programs" / Path(a.program).name
    shutil.copy2(ROOT / a.program, prog)  # frozen copy

    target = target_for(spec)
    import target_json as TJ
    TJ.save(target, out / "target.json")  # the calibration everything here is compiled for (Colab's AI step reads it)
    ctarget, nrem, bad_q = RF.avoid_dead(target)
    print(f"{spec}: compiling without {nrem} two-qubit entries on dead couplers/qubits ({len(bad_q)} dead qubits)", flush=True)
    plan = {"backend": a.backend, "spec": spec, "prepared": dt.datetime.now().isoformat(timespec="seconds"),
            "dry_run": spec.startswith("fake:"), "program": a.program, "split": a.split, "circuits": []}
    for s in a.sources:
        src = RF.load_circuit(ROOT / s)
        name = Path(s).stem
        why = conserves(src, a.split)
        if why:
            print(f"{name}: skipped, {why}"); continue
        up, down = sector_of(src, a.split)
        src_path = out / "sources" / f"{name}.qpy"
        with open(src_path, "wb") as f:
            qpy.dump(src, f)
        print(f"{name}: {src.num_qubits} qubits, ideal sector ({up}, {down})", flush=True)

        q_cands = []
        from qiskit.transpiler import generate_preset_pass_manager
        for seed in range(a.qiskit_seeds):
            c = generate_preset_pass_manager(optimization_level=3, target=ctarget, seed_transpiler=seed).run(src)
            if conformance(c, target):
                continue
            m = metrics(c, target)
            q_cands.append((cost(m, "v3"), f"seed {seed}", c, m))
        g_cands = []
        for seed in range(a.program_seeds):
            c, err, secs = RF.run_program(prog, src_path, spec, seed, a.limit)
            if c is None or conformance(c, target):
                print(f"  program seed {seed}: {err or conformance(c, target)}", flush=True); continue
            m = metrics(c, target)
            g_cands.append((cost(m, "v3"), f"seed {seed}", c, m))
            print(f"  program seed {seed}: 2q={m['two_qubit']} damage={m['damage']:.3f} ({secs:.0f} s)", flush=True)
        variants = {}
        for prefix, cands in (("qiskit", q_cands), ("program", g_cands)):
            for i, (c_cost, seed, circ, m) in enumerate(top2(cands)):
                label = prefix if i == 0 else f"{prefix}_2"
                with gzip.open(out / "compiled" / f"{name}__{label}.qpy.gz", "wb") as f:
                    qpy.dump(circ, f)
                variants[label] = {"seed": seed, "two_qubit": m["two_qubit"], "depth_2q": m["depth_2q"], "damage": m["damage"],
                                   "predicted_fidelity": math.exp(-m["damage"]), "v3_cost": c_cost}
                print(f"  {label:<9} {seed:<8} 2q={m['two_qubit']} depth2q={m['depth_2q']} damage={m['damage']:.3f}", flush=True)
        plan["circuits"].append({"name": name, "qubits": src.num_qubits, "sector": [up, down], "variants": variants})

    (out / "plan.json").write_text(json.dumps(plan, indent=1))
    write_plan_md(plan, out, tag)
    n = sum(len(c["variants"]) for c in plan["circuits"])
    print(f"\nprepared {n} circuits in frontier/hardware/{tag}/ (PLAN.md); nothing submitted.  Tag: {tag}")
    return 0


def write_plan_md(plan: dict, out: Path, tag: str) -> None:
    L = [f"# Hardware plan `{tag}`: program vs Qiskit (and the AI transpiler, if added) on {plan['backend']}", "",
         ("**Dry run on a fake backend: checks the pipeline only; cannot be submitted.**" if plan["dry_run"] else
          f"Prepared {plan['prepared']} on the live calibration (saved in target.json). "
          + ("Submitted." if plan.get("job") else "Nothing has been submitted.")), "",
         "| circuit | variant | seed | 2q gates | 2q depth | predicted damage |", "|---|---|---|---:|---:|---:|"]
    for c in plan["circuits"]:
        for label, v in c["variants"].items():
            L.append(f"| {c['name']} | {label} | {v['seed']} | {v['two_qubit']} | {v['depth_2q']} | {v['damage']:.3f} |")
    (out / "PLAN.md").write_text("\n".join(L) + "\n")


def add(a) -> int:
    """Register AI-transpiler outputs (from compile_ai_live.py) in the plan, scored on the saved calibration."""
    from qiskit import qpy
    from scoring.conformance import conformance
    from scoring.metrics import cost, metrics
    import target_json as TJ
    out = OUTDIR / a.tag
    plan = json.loads((out / "plan.json").read_text())
    if plan.get("job"):
        raise SystemExit("this plan was already submitted; prepare a new one")
    target = TJ.load(out / "target.json")
    added = 0
    for c in plan["circuits"]:
        for path in sorted((out / "compiled").glob(f"{c['name']}__ai*.qpy.gz")):
            label = path.name[:-len(".qpy.gz")].partition("__")[2]
            with gzip.open(path, "rb") as f:
                circ = qpy.load(f)[0]
            why = conformance(circ, target)
            if why:
                print(f"{c['name']} {label}: not added, {why}"); continue
            m = metrics(circ, target)
            c["variants"][label] = {"seed": "ai run", "two_qubit": m["two_qubit"], "depth_2q": m["depth_2q"],
                                    "damage": m["damage"], "predicted_fidelity": math.exp(-m["damage"]), "v3_cost": cost(m, "v3")}
            print(f"{c['name']} {label:<9} 2q={m['two_qubit']} depth2q={m['depth_2q']} damage={m['damage']:.3f}")
            added += 1
    (out / "plan.json").write_text(json.dumps(plan, indent=1))
    write_plan_md(plan, out, a.tag)
    print(f"added {added} AI-transpiler circuits to {a.tag}; submit when ready")
    return 0 if added else 1


def _measured(circ):
    from scoring.ibm import measured_copy
    return measured_copy(circ)


def submit(a) -> int:
    from qiskit import qpy
    from scoring.conformance import conformance
    from scoring.ibm import service
    from qiskit_ibm_runtime import SamplerV2
    out = OUTDIR / a.tag
    plan = json.loads((out / "plan.json").read_text())
    if plan["dry_run"]:
        raise SystemExit("this plan was prepared on a fake backend; prepare against the real chip first")
    be = service().backend(plan["backend"])
    target = be.target
    pubs, labels, problems = [], [], []
    for c in plan["circuits"]:
        for label in c["variants"]:
            with gzip.open(out / "compiled" / f"{c['name']}__{label}.qpy.gz", "rb") as f:
                circ = qpy.load(f)[0]
            why = conformance(circ, target)
            if why:
                problems.append(f"{c['name']} {label}: {why}")
            pubs.append(_measured(circ)); labels.append([c["name"], label])
    if problems and not a.force:
        print("the chip's calibration changed since prepare (a coupler or qubit is now marked unusable):\n  " +
              "\n  ".join(problems) + "\nprepare again, or pass --force to submit anyway")
        return 1
    print(f"submitting {len(pubs)} circuits x {a.shots} shots to {be.name} "
          f"(a 40-circuit job used about 47 s before; expect roughly {max(5, round(len(pubs) * 1.5))}-{len(pubs) * 4} s of chip time)")
    if not a.yes and input("type yes to submit: ").strip().lower() != "yes":
        print("not submitted"); return 1
    job = SamplerV2(mode=be).run(pubs, shots=a.shots)
    plan["job"] = {"id": job.job_id(), "shots": a.shots, "labels": labels, "submitted": dt.datetime.now().isoformat(timespec="seconds")}
    (out / "plan.json").write_text(json.dumps(plan, indent=1))
    print(f"submitted job {job.job_id()} to {be.name}.  Collect later with:  .venv/bin/python frontier/hardware_frontier.py collect --tag {a.tag}")
    return 0


def in_sector(counts: dict, sector: tuple[int, int], split: int) -> tuple[float, int]:
    """(fraction of shots with exactly `sector` electrons per half, shots).  Bitstrings are clbit n-1 ... 0."""
    shots = sum(counts.values())
    good = 0
    for bits, n in counts.items():
        b = bits.replace(" ", "")[::-1]  # b[i] = clbit i = logical qubit i
        if b[:split].count("1") == sector[0] and b[split:].count("1") == sector[1]:
            good += n
    return good / shots, shots


def collect(a) -> int:
    out = OUTDIR / a.tag
    plan = json.loads((out / "plan.json").read_text())
    if a.simulate:  # synthetic counts from the damage model: tests this code, measures nothing
        import numpy as np
        rng = np.random.default_rng(0)

        def counts_for(c, label):
            f = c["variants"][label]["predicted_fidelity"]
            up, down = c["sector"]; n = c["qubits"]; shots = 4000
            counts = {}
            for _ in range(shots):
                if rng.random() < f:
                    bits = ["0"] * n
                    for i in rng.choice(a.split, up, replace=False): bits[i] = "1"
                    for i in rng.choice(n - a.split, down, replace=False): bits[a.split + i] = "1"
                else:
                    bits = [str(int(x)) for x in rng.integers(0, 2, n)]
                k = "".join(bits)[::-1]
                counts[k] = counts.get(k, 0) + 1
            return counts
        title = f"# SIMULATED (pipeline test, not a measurement): `{a.tag}`"
    else:
        from scoring.ibm import service
        job = service().job(plan["job"]["id"])
        status = str(job.status())
        print("job status:", status)
        if "DONE" not in status:
            return 1
        res = {tuple(lab): pub.data.m.get_counts() for lab, pub in zip(plan["job"]["labels"], job.result())}

        def counts_for(c, label):
            return res[(c["name"], label)]
        title = f"# Real chip: program vs Qiskit on {plan['backend']}, job {plan['job']['id']}, {plan['job']['shots']} shots each"

    rows = []
    for c in plan["circuits"]:
        for label, v in c["variants"].items():
            frac, shots = in_sector(counts_for(c, label), tuple(c["sector"]), a.split)
            rows.append({"circuit": c["name"], "variant": label, "two_qubit": v["two_qubit"], "damage": v["damage"],
                         "in_sector": frac, "stderr": math.sqrt(max(frac * (1 - frac), 1e-12) / shots), "shots": shots})
    L = [title, "",
         f"Score: fraction of shots in the ideal electron sector (an ideal chip gives 1.0; {RANDOM_SECTOR_NOTE}). "
         "Higher is better. ± is one standard error from the shot count.", "",
         "| circuit | variant | 2q gates | predicted damage | in-sector fraction |", "|---|---|---:|---:|---:|"]
    for r in rows:
        L.append(f"| {r['circuit']} | {r['variant']} | {r['two_qubit']} | {r['damage']:.3f} | {r['in_sector']:.4f} ± {r['stderr']:.4f} |")
    L.append("")
    for c in plan["circuits"]:
        by = {r["variant"]: r for r in rows if r["circuit"] == c["name"]}
        groups = {}
        for k, r in by.items():
            groups.setdefault(k.split("_")[0], []).append(r["in_sector"])
        if "program" in groups:
            g = groups["program"]; mg = sum(g) / len(g)
            for rival in ("qiskit", "ai"):
                if rival in groups:
                    q = groups[rival]; mq = sum(q) / len(q)
                    L.append(f"- **{c['name']}**: program pair mean {mg:.4f} vs {rival} pair mean {mq:.4f} "
                             f"(ratio {mg / mq:.2f}x; both program above both {rival}: {'yes' if min(g) > max(q) else 'no'})")
    report = "\n".join(L) + "\n"
    (out / ("HARDWARE_SIMULATED.md" if a.simulate else "HARDWARE.md")).write_text(report)
    if not a.simulate:
        plan["measured"] = rows
        (out / "plan.json").write_text(json.dumps(plan, indent=1))
    print(report)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--backend", default="ibm_kingston", help="IBM chip name, or fake:<FakeBackend> for a dry run")
    p.add_argument("--sources", nargs="+", default=DEFAULT_SOURCES)
    p.add_argument("--program", required=True, help="a .py file defining compile(circuit, target, seed) -> circuit on target")
    p.add_argument("--qiskit-seeds", type=int, default=32)
    p.add_argument("--program-seeds", type=int, default=5)
    p.add_argument("--limit", type=float, default=1800.0)
    p.add_argument("--tag", default=None)
    s = sub.add_parser("submit")
    s.add_argument("--tag", required=True); s.add_argument("--shots", type=int, default=4000)
    s.add_argument("--yes", action="store_true", help="skip the confirmation prompt"); s.add_argument("--force", action="store_true")
    d = sub.add_parser("add", help="add AI-transpiler outputs made in Colab by compile_ai_live.py")
    d.add_argument("--tag", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--tag", required=True); c.add_argument("--simulate", action="store_true")
    for x in (p, s, c, d):
        x.add_argument("--split", type=int, default=32, help="first spin-down qubit")
    a = ap.parse_args(argv)
    try:
        import os
        os.nice(19 if a.cmd == "prepare" else 0)
    except OSError:
        pass
    return {"prepare": prepare, "submit": submit, "collect": collect, "add": add}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
