from core.reasoning import ProofOriginReasoner
from core.extractor import ImageSignalExtractor
from core.adapter import ExtractorAdapter


extractor = ImageSignalExtractor()
adapter = ExtractorAdapter()
reasoner = ProofOriginReasoner()

image_path = "sample_images/test.png"

metadata = extractor.extract_metadata(image_path)
extracted_signals = extractor.detect_basic_signals(metadata)

input_data = adapter.build_input_data(metadata, extracted_signals)

result = reasoner.analyze_input_data(input_data)

print(result)
