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

from core.external_engines import (
    run_sightengine_analysis,
    run_openai_vision_analysis,
)

from core.consensus_engine import (
    calculate_weighted_consensus,
)

from core.forensic_context import (
    analyze_forensic_context,
)

from core.engine_arbitration import (
    analyze_engine_disagreement,
)

from core.human_summary import (
    generate_human_summary,
)

from core.confidence_escalation import (
    apply_confidence_escalation,
)

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
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=file.filename,
    ) as temp_file:
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

    extracted_signals = extractor.detect_basic_signals(
        metadata
    )

    vision_findings = vision_engine.analyze_image(
        image_path
    )

    input_data = adapter.build_input_data(
        metadata,
        extracted_signals,
    )

    input_data["visual_findings"] += vision_findings.get(
        "visual_findings",
        [],
    )

    input_data["lighting_findings"] += vision_findings.get(
        "lighting_findings",
        [],
    )

    input_data["ai_findings"] += vision_findings.get(
        "ai_findings",
        [],
    )

    result = reasoner.analyze_input_data(input_data)

    file_id = str(uuid.uuid4())

    sightengine_result = run_sightengine_analysis(
        image_path
    )

    openai_vision_result = run_openai_vision_analysis(
        image_path
    )

    external_engines = {
        "prooforigin": {
            "status": "complete",
            "score": result.get(
                "summary",
                {},
            ).get("ai_score", 0),

            "label": result.get(
                "summary",
                {},
            ).get("label"),
        },

        "sightengine": sightengine_result,

        "openai_vision": openai_vision_result,

        "openai_reasoning": {
            "status": "pending",
            "score": None,
            "label": None,
        },
    }

    weighted_consensus = calculate_weighted_consensus(
        external_engines
    )

    forensic_context = analyze_forensic_context(
        report=result,
        external_engines=external_engines,
        metadata=metadata,
    )

    escalated_consensus = apply_confidence_escalation(
        weighted_consensus,
        forensic_context,
        external_engines,
    )

    engine_arbitration = analyze_engine_disagreement(
        external_engines
    )

    human_summary = generate_human_summary(
        escalated_consensus,
        forensic_context,
        engine_arbitration,
    )

    result["weighted_consensus"] = escalated_consensus
    result["original_consensus"] = weighted_consensus
    result["forensic_context"] = forensic_context
    result["engine_arbitration"] = engine_arbitration
    result["human_summary"] = human_summary
    result["file_id"] = file_id
    result["training_status"] = "logged_for_review"

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

    print(
        f"[ProofOrigin] Sightengine: "
        f"{sightengine_result.get('status')}"
    )

    print(
        f"[ProofOrigin] OpenAI Vision: "
        f"{openai_vision_result.get('status')}"
    )

    print(
        f"[ProofOrigin] Original consensus: "
        f"{weighted_consensus}"
    )

    print(
        f"[ProofOrigin] Escalated consensus: "
        f"{escalated_consensus}"
    )

    print(
        f"[ProofOrigin] Forensic context: "
        f"{forensic_context}"
    )

    print(
        f"[ProofOrigin] Engine arbitration: "
        f"{engine_arbitration}"
    )

    print(
        f"[ProofOrigin] Human summary: "
        f"{human_summary}"
    )

    return {
        **result,

        "file_id": file_id,

        "percent": escalated_consensus.get("score")
        if escalated_consensus.get("score") is not None
        else result.get("summary", {}).get("ai_score", 0),

        "metadata": metadata,

        "integrity": integrity,

        "proofOriginScore": result.get(
            "consensus_analysis",
            {},
        ).get("consensus_score"),

        "weightedConsensus": escalated_consensus,
        "weighted_consensus": escalated_consensus,

        "originalConsensus": weighted_consensus,
        "original_consensus": weighted_consensus,

        "confidenceEscalation": escalated_consensus,
        "confidence_escalation": escalated_consensus,

        "forensicContext": forensic_context,
        "forensic_context": forensic_context,

        "engineArbitration": engine_arbitration,
        "engine_arbitration": engine_arbitration,

        "humanSummary": human_summary,
        "human_summary": human_summary,

        "verdict": escalated_consensus.get("label")
        or result.get("summary", {}).get("label"),

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

    with open(
        evidence_path,
        "r",
        encoding="utf-8",
    ) as f:
        evidence = json.load(f)

    return {
        "success": True,
        "file_id": file_id,
        "evidence": evidence,
    }
