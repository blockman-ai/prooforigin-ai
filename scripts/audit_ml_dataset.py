#!/usr/bin/env python3
"""Audit ProofOrigin ML dataset buckets and quality signals."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.dataset_utils import DATASET_BUCKETS, audit_dataset_full


def main():
    parser = argparse.ArgumentParser(description="Audit ProofOrigin ML dataset")
    parser.add_argument(
        "--split",
        choices=["all", "train", "validation"],
        default="all",
        help="Which dataset split to audit",
    )
    args = parser.parse_args()

    report = audit_dataset_full(split=args.split)
    report["buckets_expected"] = list(DATASET_BUCKETS)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
