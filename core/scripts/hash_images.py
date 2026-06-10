import hashlib
from pathlib import Path

RAW_DIR = Path("data/raw")

def hash_file(path: Path) -> str:
    sha256 = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def main():
    for path in RAW_DIR.glob("*"):
        if path.is_file():
            print(path.name, hash_file(path))

if __name__ == "__main__":
    main()
