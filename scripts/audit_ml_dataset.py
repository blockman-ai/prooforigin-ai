#!/usr/bin/env python3
"""Audit ProofOrigin ML dataset folders."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.dataset_utils import audit_dataset_counts, validate_readable_image


def main():
    counts = audit_dataset_counts()
    unreadable_real = []
    unreadable_ai = []

    for path in counts["real_images"]:
        ok, reason = validate_readable_image(path)
        if not ok:
            unreadable_real.append({"path": str(path), "reason": reason})

    for path in counts["ai_images"]:
        ok, reason = validate_readable_image(path)
        if not ok:
            unreadable_ai.append({"path": str(path), "reason": reason})

    report = {
        "real_count": counts["real_count"],
        "ai_count": counts["ai_count"],
        "real_dir": counts["real_dir"],
        "ai_dir": counts["ai_dir"],
        "unreadable_real": unreadable_real,
        "unreadable_ai": unreadable_ai,
        "ready_for_training": counts["real_count"] >= 2 and counts["ai_count"] >= 2,
    }

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
