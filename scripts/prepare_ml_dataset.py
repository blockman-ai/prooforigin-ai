#!/usr/bin/env python3
"""Organize raw images into ml/datasets/real and ml/datasets/ai."""

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.dataset_utils import AI_DIR, REAL_DIR, is_image_file, validate_readable_image


def _unique_destination(target_dir, filename):
    target_dir.mkdir(parents=True, exist_ok=True)
    candidate = target_dir / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    index = 1
    while True:
        alt = target_dir / f"{stem}_{index}{suffix}"
        if not alt.exists():
            return alt
        index += 1


def prepare_dataset(source_dir, label, move=False, dry_run=False):
    if label not in {"real", "ai"}:
        raise SystemExit("label must be 'real' or 'ai'")

    source_dir = Path(source_dir)
    if not source_dir.is_dir():
        raise SystemExit(f"Source directory not found: {source_dir}")

    target_dir = REAL_DIR if label == "real" else AI_DIR
    copied = 0
    skipped = 0
    removed = 0

    for path in sorted(source_dir.rglob("*")):
        if not path.is_file() or not is_image_file(path):
            continue

        ok, reason = validate_readable_image(path)
        if not ok:
            skipped += 1
            print(f"skip unreadable: {path} ({reason})")
            continue

        destination = _unique_destination(target_dir, path.name)
        if dry_run:
            print(f"would copy {path} -> {destination}")
        elif move:
            shutil.move(str(path), str(destination))
        else:
            shutil.copy2(path, destination)
        copied += 1

    print(
        json_summary(
            {
                "label": label,
                "source_dir": str(source_dir),
                "target_dir": str(target_dir),
                "copied": copied,
                "skipped_unreadable": skipped,
                "mode": "move" if move else "copy",
                "dry_run": dry_run,
            }
        )
    )


def json_summary(payload):
    import json

    return json.dumps(payload, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Prepare ProofOrigin ML dataset folders")
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--label", required=True, choices=["real", "ai"])
    parser.add_argument("--move", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    prepare_dataset(
        source_dir=args.source_dir,
        label=args.label,
        move=args.move,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
