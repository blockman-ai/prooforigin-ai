from core.reasoning import ProofOriginReasoner
from core.extractor import ImageSignalExtractor


extractor = ImageSignalExtractor()
reasoner = ProofOriginReasoner()

image_path = "sample_images/test.png"

metadata = extractor.extract_metadata(image_path)
signals = extractor.detect_basic_signals(metadata)

input_data = {
    "metadata": metadata,
    "signals": signals,
}

result = reasoner.analyze_input_data(input_data)

print(result)
