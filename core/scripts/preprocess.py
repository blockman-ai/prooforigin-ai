import os
import hashlib
from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

VALID_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".heic"
}

TARGET_SIZE = (512, 512)

def generate_hash(filepath):
    sha256 = hashlib.sha256()

    with open(filepath, "rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            sha256.update(chunk)

    return sha256.hexdigest()

def process_image(input_path, output_path):
    image = Image.open(input_path)

    image = image.convert("RGB")

    image.thumbnail(TARGET_SIZE)

    canvas = Image.new("RGB", TARGET_SIZE, (0, 0, 0))

    offset_x = (TARGET_SIZE[0] - image.width) // 2
    offset_y = (TARGET_SIZE[1] - image.height) // 2

    canvas.paste(image, (offset_x, offset_y))

    canvas.save(output_path, quality=95)

def main():
    total = 0
    errors = 0

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    for label_dir in RAW_DIR.iterdir():
        if not label_dir.is_dir():
            continue

        output_label_dir = PROCESSED_DIR / label_dir.name
        output_label_dir.mkdir(parents=True, exist_ok=True)

        for image_path in label_dir.iterdir():
            if image_path.suffix.lower() not in VALID_EXTENSIONS:
                continue

            try:
                image_hash = generate_hash(image_path)

                output_filename = f"{image_hash}.jpg"

                output_path = output_label_dir / output_filename

                process_image(image_path, output_path)

                total += 1

                print(f"[OK] {image_path.name} -> {output_filename}")

            except Exception as e:
                errors += 1
                print(f"[ERROR] {image_path.name}: {e}")

    print("\n=== PREPROCESS COMPLETE ===")
    print(f"Processed: {total}")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    main()
