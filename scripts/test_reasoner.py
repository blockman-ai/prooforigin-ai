from core.reasoning import ProofOriginReasoner
from core.extractor import ImageSignalExtractor
from core.adapter import ExtractorAdapter
from core.vision import VisionForensicsEngine


extractor = ImageSignalExtractor()
adapter = ExtractorAdapter()
reasoner = ProofOriginReasoner()
vision_engine = VisionForensicsEngine()

image_path = "sample_images/test.png"

metadata = extractor.extract_metadata(image_path)
extracted_signals = extractor.detect_basic_signals(metadata)
vision_findings = vision_engine.analyze_image(image_path)

input_data = adapter.build_input_data(metadata, extracted_signals)

input_data["visual_findings"] += vision_findings["visual_findings"]
input_data["lighting_findings"] += vision_findings["lighting_findings"]
input_data["ai_findings"] += vision_findings["ai_findings"]

result = reasoner.analyze_input_data(input_data)

print(result)
