import os
from collections import Counter

DATASET_DIR = "data/processed"

def main():
    if not os.path.exists(DATASET_DIR):
        print("No processed dataset found. Run scripts/preprocess.py first.")
        return

    labels = []

    for label in os.listdir(DATASET_DIR):
        label_path = os.path.join(DATASET_DIR, label)

        if os.path.isdir(label_path):
            count = len([
                file for file in os.listdir(label_path)
                if file.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
            ])

            labels.append((label, count))

    print("\n=== TRAINING STARTER ===")
    print("This is where model training will begin later.\n")

    for label, count in labels:
        print(f"{label}: {count} images")

    print("\nNext goal: collect at least 100 images per label before real training.")

if __name__ == "__main__":
    main()print("Training pipeline coming soon.")
