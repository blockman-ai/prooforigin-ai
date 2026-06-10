import os
from functools import lru_cache

_heif_registered = False

RUNTIME_DATA_DIRS = (
    "data",
    "data/evidence",
    "data/training",
    "data/disagreements",
    "data/anchors",
    "data/anchors/batches",
)


def ensure_runtime_dirs():
    for directory in RUNTIME_DATA_DIRS:
        os.makedirs(directory, exist_ok=True)


def ensure_heif_opener():
    global _heif_registered
    if _heif_registered:
        return

    try:
        from pillow_heif import register_heif_opener

        register_heif_opener()
        _heif_registered = True
    except Exception:
        pass


@lru_cache(maxsize=1)
def get_reasoner():
    from core.reasoning import ProofOriginReasoner

    return ProofOriginReasoner()


@lru_cache(maxsize=1)
def get_extractor():
    from core.extractor import ImageSignalExtractor

    return ImageSignalExtractor()


@lru_cache(maxsize=1)
def get_adapter():
    from core.adapter import ExtractorAdapter

    return ExtractorAdapter()


@lru_cache(maxsize=1)
def get_vision_engine():
    from core.vision import VisionForensicsEngine

    return VisionForensicsEngine()


@lru_cache(maxsize=1)
def get_dataset_logger():
    from core.dataset_logger import DatasetLogger

    return DatasetLogger()
