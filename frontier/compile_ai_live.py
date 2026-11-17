"""Compile a hardware plan's circuits with IBM's AI transpiler on the plan's saved live calibration.
Runs where qiskit-ibm-transpiler installs (Colab); the Mac then adds the results with
`hardware_frontier.py add --tag <tag>`.

    python frontier/compile_ai_live.py frontier/hardware/<tag> --runs 2

Uses <tag>/target.json (written by `hardware_frontier.py prepare`), broken couplers removed except where
that would split the chip (the AI router fails on a split chip), exactly as run_frontier.py does for
its AI row.  Writes <tag>/compiled/<circuit>__ai.qpy.gz and __ai_2 (a second run; the AI layout search
is randomised, so two runs give the pair the other compilers have).
"""
from __future__ import annotations

import argparse
import gzip
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontier"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan_dir", type=Path)
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--base", default="FakeFez", help="any 156-qubit fake backend; only its Target is replaced")
    a = ap.parse_args()
    from qiskit import qpy
    from qiskit_ibm_runtime import fake_provider as fp
    from qiskit_ibm_transpiler import generate_ai_pass_manager
    import run_frontier as RF
    import target_json as TJ
    d = a.plan_dir if a.plan_dir.is_absolute() else ROOT / a.plan_dir
    (d / "compiled").mkdir(exist_ok=True)
    target = TJ.load(d / "target.json")
    ai_target = RF.avoid_dead(target, keep_connected=True)[0]
    backend = getattr(fp, a.base)()
    backend._target = ai_target
    assert backend.target is ai_target, "could not swap the fake backend's Target"
    for src_path in sorted((d / "sources").glob("*.qpy")):
        with open(src_path, "rb") as f:
            src = qpy.load(f)[0]
        for r in range(a.runs):
            out = generate_ai_pass_manager(backend=backend, optimization_level=3, ai_optimization_level=3).run(src)
            label = "ai" if r == 0 else f"ai_{r + 1}"
            with gzip.open(d / "compiled" / f"{src_path.stem}__{label}.qpy.gz", "wb") as f:
                qpy.dump(out, f)
            n2 = sum(1 for i in out.data if i.operation.num_qubits == 2)
            print(f"{src_path.stem} {label}: {n2} two-qubit gates", flush=True)
    print("done: bring", d / "compiled", "back to the Mac and run hardware_frontier.py add")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
