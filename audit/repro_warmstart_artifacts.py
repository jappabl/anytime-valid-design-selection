#!/usr/bin/env python3
"""Re-run the warm-start experiment mains IN MEMORY and diff against the
published artifacts.

The published files carry a SHA256-16 checksum of their own body. Each script's
`main()` is pure (only the `if __name__ == "__main__"` block writes to disk),
so this reproduces the artifact body without touching any repo file.

    python3 audit/repro_warmstart_artifacts.py [warmstart|joint|stress|drift ...]

Prints, per artifact: recomputed checksum, published checksum, match verdict,
and a unified diff of the first differing lines if they disagree.
"""

import difflib
import hashlib
import importlib.util
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

TARGETS = {
    "warmstart": ("scripts/run_warmstart.py", "results_warmstart.txt"),
    "joint": ("scripts/run_warmstart_joint.py", "results_warmstart_joint.txt"),
    "stress": ("scripts/run_warmstart_stress.py", "results_warmstart_stress.txt"),
    "drift": ("scripts/run_warmstart_drift.py", "results_warmstart_drift.txt"),
}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    which = sys.argv[1:] or list(TARGETS)
    for key in which:
        script, artifact = TARGETS[key]
        spath, apath = REPO / script, REPO / artifact
        if not spath.exists() or not apath.exists():
            print(f"{key}: MISSING ({script} / {artifact})")
            continue
        mod = load(f"_repro_{key}", spath)
        buf = io.StringIO()
        with redirect_stdout(buf):
            mod.main()
        body = buf.getvalue()
        got = hashlib.sha256(body.encode()).hexdigest()[:16]
        published = apath.read_text()
        pub_sum = ""
        for line in published.splitlines():
            if line.startswith("Checksum (SHA256):"):
                pub_sum = line.split(":", 1)[1].strip()
        pub_body = published.split("\n" + "=" * 76 + "\nChecksum")[0]
        ok = got == pub_sum
        print(f"{key:10s} recomputed {got}  published {pub_sum}  "
              f"{'MATCH' if ok else 'MISMATCH'}")
        sys.stdout.flush()
        if not ok:
            d = list(difflib.unified_diff(
                pub_body.splitlines(), body.splitlines(),
                "published", "recomputed", lineterm="", n=1))
            print("\n".join(d[:60]))
        print()


if __name__ == "__main__":
    main()
