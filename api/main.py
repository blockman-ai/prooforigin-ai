from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import shutil
import uuid
import json
import os

from core.reasoning import ProofOriginReasoner
from core.extractor import ImageSignalExtractor
from core.adapter import ExtractorAdapter
from core.vision import VisionForensicsEngine
from core.dataset_logger import DatasetLogger
from api.feedback import router as feedback_router


app = FastAPI(title="ProofOrigin AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://prooforigin.org",
        "https://www.prooforigin.org",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(feedback_router)

reasoner = ProofOriginReasoner()
extractor = ImageSignalExtractor()
adapter = ExtractorAdapter()
vision_engine = VisionForensicsEngine()
dataset_logger = DatasetLogger()


@app.get("/")
def root():
    return {
        "name": "ProofOrigin AI",
        "status": "running",
        "mission": "Media authenticity research and forensic intelligence.",
    }


@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        image_path = temp_file.name

    metadata = extractor.extract_metadata(image_path)
    extracted_signals = extractor.detect_basic_signals(metadata)
    vision_findings = vision_engine.analyze_image(image_path)

    input_data = adapter.build_input_data(metadata, extracted_signals)

    input_data["visual_findings"] += vision_findings.get("visual_findings", [])
    input_data["lighting_findings"] += vision_findings.get("lighting_findings", [])
    input_data["ai_findings"] += vision_findings.get("ai_findings", [])

    result = reasoner.analyze_input_data(input_data)

    file_id = str(uuid.uuid4())

    dataset_logger.log_analysis(
        file_id=file_id,
        report=result,
        external_engines={
            "sightengine": "pending",
            "openai_vision": "pending",
            "openai_reasoning": "pending",
        },
    )

    print(f"[ProofOrigin] Evidence logged: {file_id}")

    result["file_id"] = file_id
    result["training_status"] = "logged_for_review"

    return {
        **result,
        "percent": result.get("summary", {}).get("ai_score", 0),
        "metadata": metadata,
        "proofOriginScore": result.get("consensus_analysis", {}).get(
            "consensus_score"
        ),
        "verdict": result.get("summary", {}).get("label"),
    }


@app.get("/evidence/{file_id}")
def get_evidence(file_id: str):
    evidence_path = f"data/evidence/{file_id}.json"

    if not os.path.exists(evidence_path):
        return {
            "success": False,
            "error": "Evidence record not found",
            "file_id": file_id,
        }

    with open(evidence_path, "r", encoding="utf-8") as f:
        evidence = json.load(f)

    return {
        "success": True,
        "file_id": file_id,
        "evidence": evidence,
    }
