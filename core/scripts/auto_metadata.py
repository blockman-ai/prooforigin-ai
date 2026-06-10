import csv
from pathlib import Path

RAW_DIR = Path("data/raw")
METADATA_FILE = Path("data/metadata/labels.csv")

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}

FIELDNAMES = [
    "filename",
    "label",
    "source",
    "detector_score",
    "human_feedback",
    "final_label",
]

FINAL_LABELS = {
    "real": "confirmed_real",
    "ai_generated": "confirmed_ai",
    "edited": "confirmed_edited",
    "manipulated": "confirmed_manipulated",
    "screenshot": "confirmed_screenshot",
}

def load_existing():
    if not METADATA_FILE.exists():
        return set(), []

    with METADATA_FILE.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    existing = {row["filename"] for row in rows}
    return existing, rows

def main():
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing, rows = load_existing()
    added = 0

    for label_dir in RAW_DIR.iterdir():
        if not label_dir.is_dir():
            continue

        label = label_dir.name

        for image_path in label_dir.iterdir():
            if image_path.suffix.lower() not in VALID_EXTENSIONS:
                continue

            if image_path.name in existing:
                continue

            rows.append({
                "filename": image_path.name,
                "label": label,
                "source": "manual_upload",
                "detector_score": "1.0" if label == "ai_generated" else "0.0",
                "human_feedback": "confirmed",
                "final_label": FINAL_LABELS.get(label, label),
            })

            added += 1

    with METADATA_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Metadata updated. Added {added} new files.")

if __name__ == "__main__":
    main()
