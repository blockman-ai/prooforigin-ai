from fastapi import FastAPI, UploadFile, File
import tempfile
import shutil

from core.reasoning import ProofOriginReasoner
from core.extractor import ImageSignalExtractor
from core.adapter import ExtractorAdapter
from core.vision import VisionForensicsEngine

app = FastAPI(title="ProofOrigin AI API")

reasoner = ProofOriginReasoner()
extractor = ImageSignalExtractor()
adapter = ExtractorAdapter()
vision_engine = VisionForensicsEngine()


@app.get("/")
def root():
    return {
        "name": "ProofOrigin AI",
        "status": "running",
        "mission": "Media authenticity research and forensic intelligence."
    }


@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):

    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        image_path = temp_file.name

    metadata = extractor.extract_metadata(image_path)

    extracted_signals = extractor.detect_basic_signals(metadata)

    vision_findings = vision_engine.analyze_image(image_path)

    input_data = adapter.build_input_data(
        metadata,
        extracted_signals
    )

    input_data["visual_findings"] += (
        vision_findings["visual_findings"]
    )

    input_data["lighting_findings"] += (
        vision_findings["lighting_findings"]
    )

    input_data["ai_findings"] += (
        vision_findings["ai_findings"]
    )

    result = reasoner.analyze_input_data(input_data)

    return result
