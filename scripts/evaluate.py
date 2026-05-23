import os
from PIL import Image

DATASET_DIR = "data/processed"

def evaluate_dataset():
    total_images = 0
    labels = {}

    for label in os.listdir(DATASET_DIR):
        label_path = os.path.join(DATASET_DIR, label)

        if not os.path.isdir(label_path):
            continue

        count = 0

        for filename in os.listdir(label_path):
            filepath = os.path.join(label_path, filename)

            try:
                img = Image.open(filepath)
                img.verify()
                count += 1
                total_images += 1

            except Exception as e:
                print(f"[BROKEN] {filename}: {e}")

        labels[label] = count

    print("\n=== DATASET REPORT ===")

    for label, count in labels.items():
        print(f"{label}: {count} images")

    print(f"\nTOTAL IMAGES: {total_images}")

if __name__ == "__main__":
    evaluate_dataset()print("Evaluation pipeline coming soon.")
