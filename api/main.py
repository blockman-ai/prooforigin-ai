from fastapi import Depends, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import uuid
import json
import os
import hashlib
from datetime import datetime

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
from core.engine_sanitize import sanitize_external_engines
from api.feedback import router as feedback_router
from core.bitcoin_lite_anchor import queue_lite_anchor
from core.merkle_settlement import create_merkle_batch
from core.proof_verifier import verify_proof_record, verify_uploaded_file_hash
from core.bundle_store import load_evidence_bundle, verify_bundle_integrity
from core.public_report import PUBLIC_REPORT_FIELDS, build_public_report
from core.website_contract import (
    build_website_contract_from_evidence,
    with_camel_case_contract,
)
from core.protocol import (
    VERIFIED_SCOPE_BUNDLE_AND_FILE_HASH,
    VERIFIED_SCOPE_NONE,
    VERIFIED_SCOPE_PARTIAL,
)
from api.response_utils import RESPONSE_SCHEMA_VERSION, LEGACY_DUPLICATE_KEYS_NOTE
from api.security import (
    read_upload_with_limit,
    require_api_key,
    validate_optional_api_key,
    validate_upload_file,
)
from api.response_utils import build_analyze_response
from core.policy_engine import apply_constitution_policy, build_engine_snapshot_hash
from core.evidence_schema import build_evidence_record


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


def _cleanup_temp_paths(temp_paths):
    for path in temp_paths:
        if path and os.path.exists(path):
            try:
                os.unlink(path)
            except OSError:
                pass


@app.get("/")
def root():
    return {
        "name": "ProofOrigin AI",
        "status": "running",
        "mission": "Media authenticity research and forensic intelligence.",
    }


@app.post("/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    _: None = Depends(validate_optional_api_key),
):
    validate_upload_file(file)

    temp_paths = []
    original_image_path = None

    try:
        original_file_bytes = await read_upload_with_limit(file)

        suffix = os.path.splitext(file.filename or "")[1] or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(original_file_bytes)
            original_image_path = temp_file.name
            temp_paths.append(original_image_path)

        original_file_hash = hashlib.sha256(original_file_bytes).hexdigest()
        original_file_size = len(original_file_bytes)

        original_metadata = extractor.extract_metadata(original_image_path)

        image_path = original_image_path
        analysis_file_type = file.content_type
        was_converted = False

        filename_lower = (file.filename or "").lower()

        if filename_lower.endswith(".heic") or filename_lower.endswith(".heif"):
            converted_path = image_path + ".jpg"

            image = Image.open(image_path)
            image = image.convert("RGB")
            image.save(converted_path, format="JPEG", quality=95)

            image_path = converted_path
            temp_paths.append(converted_path)
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

        policy_result = apply_constitution_policy(
            final_consensus=final_consensus,
            original_consensus=original_consensus,
            engine_arbitration=engine_arbitration,
            external_engines=external_engines,
            forensic_context=forensic_context,
            existing_warnings=result.get("warnings", []),
        )

        engine_snapshot_hash = build_engine_snapshot_hash(external_engines)

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
        result["policy"] = policy_result
        result["decision_tier"] = policy_result["decision_tier"]
        result["constitution_version"] = policy_result["constitution_version"]
        result["confidence_in_estimate"] = policy_result["confidence_in_estimate"]
        result["uncertainty_notes"] = policy_result["uncertainty_notes"]
        result["warnings"] = policy_result["warnings"]
        result["engine_snapshot_hash"] = engine_snapshot_hash

        analysis_timestamp = datetime.utcnow().isoformat()
        evidence_preview = build_evidence_record(
            file_id=file_id,
            timestamp=analysis_timestamp,
            report=result,
            external_engines=external_engines,
            file_hash=original_file_hash,
            file_name=file.filename,
            file_type=file.content_type,
            file_size=original_file_size,
            policy=policy_result,
        )
        evidence_bundle_hash = evidence_preview["evidence_bundle_hash"]

        bitcoin_lite_anchor = queue_lite_anchor(
            file_id=file_id,
            integrity=integrity,
            verdict=final_consensus.get("label")
            or result.get("summary", {}).get("label"),
            evidence_bundle_hash=evidence_bundle_hash,
        )
        result["bitcoin_lite_anchor"] = bitcoin_lite_anchor

        log_entry = dataset_logger.log_analysis(
            file_id=file_id,
            report=result,
            external_engines=external_engines,
            file_hash=original_file_hash,
            file_name=file.filename,
            file_type=file.content_type,
            file_size=original_file_size,
            timestamp=analysis_timestamp,
        )

        result["evidence_bundle_hash"] = log_entry.get("evidence_bundle_hash")
        result["policy_hash"] = log_entry.get("policy_hash")

        print(f"[ProofOrigin] Evidence logged: {file_id}")
        print(f"[ProofOrigin] Original SHA-256: {original_file_hash}")
        print(f"[ProofOrigin] Analysis SHA-256: {analysis_file_hash}")
        print(f"[ProofOrigin] Converted: {was_converted}")
        print(f"[ProofOrigin] Camera authenticity: {camera_authenticity}")
        print(f"[ProofOrigin] Camera provenance: {camera_provenance}")

        return build_analyze_response(
            result=result,
            file_id=file_id,
            metadata=metadata,
            original_metadata=original_metadata,
            converted_metadata=converted_metadata,
            integrity=integrity,
            final_consensus=final_consensus,
            original_consensus=original_consensus,
            forensic_context=forensic_context,
            engine_arbitration=engine_arbitration,
            human_summary=human_summary,
            contradiction_resolution=contradiction_resolution,
            camera_authenticity=camera_authenticity,
            camera_provenance=camera_provenance,
            bitcoin_lite_anchor=bitcoin_lite_anchor,
            external_engines=external_engines,
        )
    finally:
        _cleanup_temp_paths(temp_paths)


@app.post("/settle/merkle")
def settle_merkle_batch(_: None = Depends(require_api_key)):
    batch = create_merkle_batch()
    return batch


@app.get("/verify-proof/{file_id}")
def verify_proof(
    file_id: str,
    _: None = Depends(require_api_key),
):
    return verify_proof_record(file_id)


@app.post("/verify")
async def verify_uploaded_file(
    file_id: str = Form(...),
    file: UploadFile = File(...),
):
    validate_upload_file(file)
    file_bytes = await read_upload_with_limit(file)
    uploaded_sha256 = hashlib.sha256(file_bytes).hexdigest()
    return verify_uploaded_file_hash(file_id, uploaded_sha256)


@app.get("/report/{file_id}")
def get_public_report(file_id: str):
    evidence = load_evidence_bundle("data/evidence", file_id)

    if evidence is None:
        return {
            "success": False,
            "error": "Report not found",
            "file_id": file_id,
        }

    report = build_public_report(evidence)

    return {
        "success": True,
        "report": report,
        "schema_fields": list(PUBLIC_REPORT_FIELDS),
    }


@app.get("/evidence/{file_id}")
def get_evidence(
    file_id: str,
    _: None = Depends(require_api_key),
):
    evidence = load_evidence_bundle("data/evidence", file_id)

    if evidence is None:
        return {
            "success": False,
            "error": "Evidence record not found",
            "file_id": file_id,
        }

    if "engine_outputs" in evidence:
        evidence["engine_outputs"] = sanitize_external_engines(evidence["engine_outputs"])

    bundle_check = verify_bundle_integrity(evidence)
    integrity = evidence.get("integrity") or {}
    has_file_hashes = bool(
        integrity.get("original_sha256") and integrity.get("analysis_sha256")
    )
    if bundle_check["hash_match"] and has_file_hashes:
        verified_scope = VERIFIED_SCOPE_BUNDLE_AND_FILE_HASH
    elif bundle_check["hash_match"] or has_file_hashes:
        verified_scope = VERIFIED_SCOPE_PARTIAL
    else:
        verified_scope = VERIFIED_SCOPE_NONE

    contract = build_website_contract_from_evidence(
        evidence,
        verified_scope=verified_scope,
    )
    contract_camel = with_camel_case_contract(contract)
    evidence_payload = {**evidence, "contract": contract}

    return {
        "success": True,
        "file_id": file_id,
        "evidence": evidence_payload,
        **contract,
        **contract_camel,
        "truth_verified": False,
        "response_meta": {
            "schema_version": RESPONSE_SCHEMA_VERSION,
            "legacy_duplicate_keys": LEGACY_DUPLICATE_KEYS_NOTE,
            "website_fields": list(contract.keys()),
        },
    }
