from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import shutil
import uuid
import json
import os
import hashlib

from PIL import Image
from pillow_heif import register_heif_opener

from core.reasoning import ProofOriginReasoner
from core.extractor import ImageSignalExtractor
from core.adapter import ExtractorAdapter
from core.vision import VisionForensicsEngine
from core.dataset_logger import DatasetLogger
from core.external_engines import run_sightengine_analysis, run_openai_vision_analysis
from core.consensus_engine import calculate_weighted_consensus
from core.forensic_context import analyze_forensic_context
from core.engine_arbitration import analyze_engine_disagreement
from core.human_summary import generate_human_summary
from core.confidence_escalation import apply_confidence_escalation
from core.contradiction_resolution import resolve_forensic_contradictions
from core.camera_authenticity import analyze_camera_authenticity
from core.camera_provenance import classify_camera_provenance
from api.feedback import router as feedback_router
from core.bitcoin_lite_anchor import queue_lite_anchor
from core.merkle_settlement import create_merkle_batch
from core.proof_verifier import verify_proof_record


register_heif_opener()

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
        original_image_path = temp_file.name

    with open(original_image_path, "rb") as f:
        original_file_bytes = f.read()

    original_file_hash = hashlib.sha256(original_file_bytes).hexdigest()
    original_file_size = len(original_file_bytes)

    original_metadata = extractor.extract_metadata(original_image_path)

    image_path = original_image_path
    analysis_file_type = file.content_type
    was_converted = False

    if (
        file.filename.lower().endswith(".heic")
        or file.filename.lower().endswith(".heif")
    ):
        converted_path = image_path + ".jpg"

        image = Image.open(image_path)
        image = image.convert("RGB")
        image.save(converted_path, format="JPEG", quality=95)

        image_path = converted_path
        analysis_file_type = "image/jpeg"
        was_converted = True

    with open(image_path, "rb") as f:
        analysis_file_bytes = f.read()

    analysis_file_hash = hashlib.sha256(analysis_file_bytes).hexdigest()
    analysis_file_size = len(analysis_file_bytes)

    converted_metadata = extractor.extract_metadata(image_path)

    metadata = original_metadata if original_metadata else converted_metadata

    integrity = {
        "original_sha256": original_file_hash,
        "analysis_sha256": analysis_file_hash,
        "file_name": file.filename,
        "original_file_type": file.content_type,
        "analysis_file_type": analysis_file_type,
        "original_file_size": original_file_size,
        "analysis_file_size": analysis_file_size,
        "was_converted": was_converted,
        "conversion": "HEIC/HEIF to JPEG" if was_converted else "none",
        "hash_algorithm": "SHA-256",
        "verification_status": "hash_recorded",
        "tamper_evidence": "available",
    }

    extracted_signals = extractor.detect_basic_signals(metadata)
    vision_findings = vision_engine.analyze_image(image_path)

    input_data = adapter.build_input_data(metadata, extracted_signals)

    input_data["visual_findings"] += vision_findings.get("visual_findings", [])
    input_data["lighting_findings"] += vision_findings.get("lighting_findings", [])
    input_data["ai_findings"] += vision_findings.get("ai_findings", [])

    result = reasoner.analyze_input_data(input_data)

    camera_authenticity = analyze_camera_authenticity(result, metadata)
    camera_provenance = classify_camera_provenance(result, metadata)

    file_id = str(uuid.uuid4())

    sightengine_result = run_sightengine_analysis(image_path)
    openai_vision_result = run_openai_vision_analysis(image_path)

    external_engines = {
        "prooforigin": {
            "status": "complete",
            "score": result.get("summary", {}).get("ai_score", 0),
            "label": result.get("summary", {}).get("label"),
        },
        "sightengine": sightengine_result,
        "openai_vision": openai_vision_result,
        "openai_reasoning": {
            "status": "pending",
            "score": None,
            "label": None,
        },
    }

    original_consensus = calculate_weighted_consensus(external_engines)

    forensic_context = analyze_forensic_context(
        report=result,
        external_engines=external_engines,
        metadata=metadata,
    )

    engine_arbitration = analyze_engine_disagreement(external_engines)

    final_consensus = apply_confidence_escalation(
        original_consensus,
        forensic_context,
        external_engines,
    )

    human_summary = generate_human_summary(
        original_consensus,
        forensic_context,
        engine_arbitration,
        final_consensus,
    )

    contradiction_resolution = resolve_forensic_contradictions(
        original_consensus,
        forensic_context,
        engine_arbitration,
        final_consensus,
    )

    bitcoin_lite_anchor = queue_lite_anchor(
    file_id=file_id,
    integrity=integrity,
    verdict=final_consensus.get("label")
    or result.get("summary", {}).get("label"),
    report=result,
    )

    result["weighted_consensus"] = final_consensus
    result["original_consensus"] = original_consensus
    result["forensic_context"] = forensic_context
    result["engine_arbitration"] = engine_arbitration
    result["confidence_escalation"] = final_consensus
    result["human_summary"] = human_summary
    result["contradiction_resolution"] = contradiction_resolution
    result["camera_authenticity"] = camera_authenticity
    result["camera_provenance"] = camera_provenance
    result["integrity"] = integrity
    result["file_id"] = file_id
    result["training_status"] = "logged_for_review"
    result["bitcoin_lite_anchor"] = bitcoin_lite_anchor

    dataset_logger.log_analysis(
        file_id=file_id,
        report=result,
        external_engines=external_engines,
        file_hash=original_file_hash,
        file_name=file.filename,
        file_type=file.content_type,
        file_size=original_file_size,
    )

    print(f"[ProofOrigin] Evidence logged: {file_id}")
    print(f"[ProofOrigin] Original SHA-256: {original_file_hash}")
    print(f"[ProofOrigin] Analysis SHA-256: {analysis_file_hash}")
    print(f"[ProofOrigin] Converted: {was_converted}")
    print(f"[ProofOrigin] Camera authenticity: {camera_authenticity}")
    print(f"[ProofOrigin] Camera provenance: {camera_provenance}")

    return {
        **result,
        "file_id": file_id,
        "percent": final_consensus.get("score")
        if final_consensus.get("score") is not None
        else result.get("summary", {}).get("ai_score", 0),
        "metadata": metadata,
        "originalMetadata": original_metadata,
        "convertedMetadata": converted_metadata,
        "integrity": integrity,
        "proofOriginScore": result.get("consensus_analysis", {}).get(
            "consensus_score"
        ),
        "weightedConsensus": final_consensus,
        "weighted_consensus": final_consensus,
        "originalConsensus": original_consensus,
        "original_consensus": original_consensus,
        "confidenceEscalation": final_consensus,
        "confidence_escalation": final_consensus,
        "forensicContext": forensic_context,
        "forensic_context": forensic_context,
        "engineArbitration": engine_arbitration,
        "engine_arbitration": engine_arbitration,
        "humanSummary": human_summary,
        "human_summary": human_summary,
        "contradictionResolution": contradiction_resolution,
        "contradiction_resolution": contradiction_resolution,
        "cameraAuthenticity": camera_authenticity,
        "camera_authenticity": camera_authenticity,
        "cameraProvenance": camera_provenance,
        "camera_provenance": camera_provenance,
        "bitcoinLiteAnchor":
bitcoin_lite_anchor,
"bitcoin_lite_anchor":
bitcoin_lite_anchor,
        "verdict": final_consensus.get("label")
        or result.get("summary", {}).get("label"),
        "engine_outputs": external_engines,
    }
    


@app.post("/settle/merkle")
def settle_merkle_batch():
    batch = create_merkle_batch()
    return batch

@app.get("/verify-proof/{file_id}")
def verify_proof(file_id: str):
    return verify_proof_record(file_id)


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
