from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import shutil
import uuid
import json
import os
import hashlib

from core.reasoning import ProofOriginReasoner
from core.extractor import ImageSignalExtractor
from core.adapter import ExtractorAdapter
from core.vision import VisionForensicsEngine
from core.dataset_logger import DatasetLogger
from core.external_engines import run_sightengine_analysis
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

    with open(image_path, "rb") as f:
        file_bytes = f.read()

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    file_size = len(file_bytes)

    integrity = {
        "sha256": file_hash,
        "file_name": file.filename,
        "file_type": file.content_type,
        "file_size": file_size,
        "hash_algorithm": "SHA-256",
        "verification_status": "hash_recorded",
        "tamper_evidence": "available",
    }

    metadata = extractor.extract_metadata(image_path)
    extracted_signals = extractor.detect_basic_signals(metadata)
    vision_findings = vision_engine.analyze_image(image_path)

    input_data = adapter.build_input_data(metadata, extracted_signals)

    input_data["visual_findings"] += vision_findings.get("visual_findings", [])
    input_data["lighting_findings"] += vision_findings.get("lighting_findings", [])
    input_data["ai_findings"] += vision_findings.get("ai_findings", [])

    result = reasoner.analyze_input_data(input_data)

    file_id = str(uuid.uuid4())

    sightengine_result = run_sightengine_analysis(image_path)

    external_engines = {
        "prooforigin": {
            "status": "complete",
            "score": result.get("summary", {}).get("ai_score", 0),
            "label": result.get("summary", {}).get("label"),
        },
        "sightengine": sightengine_result,
        "openai_vision": {
            "status": "pending",
            "score": None,
            "label": None,
        },
        "openai_reasoning": {
            "status": "pending",
            "score": None,
            "label": None,
        },
    }

    dataset_logger.log_analysis(
        file_id=file_id,
        report=result,
        external_engines=external_engines,
        file_hash=file_hash,
        file_name=file.filename,
        file_type=file.content_type,
        file_size=file_size,
    )

    print(f"[ProofOrigin] Evidence logged: {file_id}")
    print(f"[ProofOrigin] SHA-256: {file_hash}")
    print(f"[ProofOrigin] Sightengine: {sightengine_result.get('status')}")

    result["file_id"] = file_id
    result["training_status"] = "logged_for_review"

    return {
        **result,
        "file_id": file_id,
        "percent": result.get("summary", {}).get("ai_score", 0),
        "metadata": metadata,
        "integrity": integrity,
        "proofOriginScore": result.get("consensus_analysis", {}).get(
            "consensus_score"
        ),
        "verdict": result.get("summary", {}).get("label"),
        "engine_outputs": external_engines,
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
