"""Re-check the saved outputs of a frontier run with a much longer time limit.

    nice -n 19 .venv/bin/python frontier/recheck.py frontier/results/<run> --only floquet --timeout 1800

For every compiled output in <run>/compiled/ (optionally only those whose name contains --only), the
source it was compiled from (<run>/sources/) and the output are checked with harness.verify: qcec's
alternating checker, then qcec's random-basis simulations if that cannot decide, each with --timeout
seconds.  Results go to <run>/RECHECK.md and recheck.json; nothing is recompiled.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run", type=Path, help="a frontier/results/<timestamp> folder")
    ap.add_argument("--only", default=None, help="only outputs whose file name contains this text")
    ap.add_argument("--timeout", type=float, default=1800.0, help="seconds per checking stage")
    a = ap.parse_args()
    try:
        os.nice(19)
    except OSError:
        pass
    from qiskit import qpy
    from harness.verify import verify

    run = a.run if a.run.is_absolute() else ROOT / a.run
    outs = sorted((run / "compiled").glob("*.qpy.gz"))
    if a.only:
        outs = [p for p in outs if a.only in p.name]
    if not outs:
        print("no compiled outputs match"); return 1
    results = []
    for p in outs:
        circuit, _, compiler = p.name[:-len(".qpy.gz")].partition("__")
        src_path = run / "sources" / f"{circuit}.qpy"
        if not src_path.exists():
            print(f"{p.name}: no source at {src_path.name}, skipped"); continue
        with open(src_path, "rb") as f:
            src = qpy.load(f)[0]
        with gzip.open(p, "rb") as f:
            out = qpy.load(f)[0]
        print(f"{circuit} / {compiler}: checking (up to {2 * a.timeout / 60:.0f} min)...", flush=True)
        t0 = time.perf_counter()
        v = verify(src, out, timeout=a.timeout)
        rec = {"circuit": circuit, "compiler": compiler, "status": v["status"], "proven": v["passed"],
               "probable": v["probable"], "stage": v.get("stage"), "minutes": round((time.perf_counter() - t0) / 60, 1)}
        verdict = "PROVEN" if v["passed"] else "PROBABLE (random tests agree)" if v["probable"] else \
                  "REFUTED" if v["status"].startswith("not_equivalent") or v["status"] == "probably_not_equivalent" else "UNDECIDED"
        rec["verdict"] = verdict
        print(f"  -> {verdict} ({v['status']}, {rec['minutes']} min)", flush=True)
        results.append(rec)
        (run / "recheck.json").write_text(json.dumps(results, indent=1))
        L = [f"# Recheck — {datetime.now():%Y-%m-%d %H:%M}", "", f"Time limit {a.timeout:.0f} s per stage.", "",
             "| circuit | compiler | verdict | qcec status | minutes |", "|---|---|---|---|---:|"]
        L += [f"| {r['circuit']} | {r['compiler']} | {r['verdict']} | {r['status']} | {r['minutes']} |" for r in results]
        (run / "RECHECK.md").write_text("\n".join(L) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
