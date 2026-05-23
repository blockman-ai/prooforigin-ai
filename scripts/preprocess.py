import os
import hashlib
from PIL import Image

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"

VALID_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]

os.makedirs(PROCESSED_DIR, exist_ok=True)

def generate_hash(filepath):
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def process_image(input_path, output_path):
    image = Image.open(input_path).convert("RGB")
    image = image.resize((512, 512))
    image.save(output_path, quality=95)

def main():
    total = 0

    for label in os.listdir(RAW_DIR):
        label_path = os.path.join(RAW_DIR, label)

        if not os.path.isdir(label_path):
            continue

        output_label_dir = os.path.join(PROCESSED_DIR, label)
        os.makedirs(output_label_dir, exist_ok=True)

        for filename in os.listdir(label_path):
            ext = os.path.splitext(filename)[1].lower()

            if ext not in VALID_EXTENSIONS:
                continue

            input_path = os.path.join(label_path, filename)

            image_hash = generate_hash(input_path)

            output_filename = f"{image_hash}.jpg"
            output_path = os.path.join(output_label_dir, output_filename)

            try:
                process_image(input_path, output_path)
                total += 1
                print(f"[OK] {filename} -> {output_filename}")

            except Exception as e:
                print(f"[ERROR] {filename}: {e}")

    print(f"\nProcessed {total} images.")

if __name__ == "__main__":
    main()print("Preprocessing pipeline coming soon.")
