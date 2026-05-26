import base64
import json
import os
import requests
from openai import OpenAI


SIGHTENGINE_USER = os.getenv("SIGHTENGINE_USER")
SIGHTENGINE_SECRET = os.getenv("SIGHTENGINE_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def run_sightengine_analysis(image_path):
    if not SIGHTENGINE_USER or not SIGHTENGINE_SECRET:
        return {
            "status": "unconfigured",
            "score": None,
            "label": "Sightengine API not configured",
        }

    try:
        with open(image_path, "rb") as image_file:
            response = requests.post(
                "https://api.sightengine.com/1.0/check.json",
                files={"media": image_file},
                data={
                    "models": "genai",
                    "api_user": SIGHTENGINE_USER,
                    "api_secret": SIGHTENGINE_SECRET,
                },
                timeout=60,
            )

        data = response.json()
        ai_score = data.get("type", {}).get("ai_generated", 0)
        score_percent = round(float(ai_score) * 100)

        if score_percent >= 75:
            label = "Likely AI Generated"
        elif score_percent >= 40:
            label = "Possibly AI Generated"
        else:
            label = "Likely Human-Made"

        return {
            "status": "complete",
            "score": score_percent,
            "label": label,
            "raw": data,
        }

    except Exception as e:
        return {
            "status": "failed",
            "score": None,
            "label": str(e),
        }


def run_openai_vision_analysis(image_path):
    if not OPENAI_API_KEY or openai_client is None:
        return {
            "status": "unconfigured",
            "score": None,
            "label": "OpenAI API not configured",
        }

    try:
        with open(image_path, "rb") as image_file:
            image_b64 = base64.b64encode(image_file.read()).decode("utf-8")

        response = openai_client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": """
Analyze this image for AI-generation and digital synthesis indicators.

Return ONLY valid JSON with this exact structure:
{
  "ai_score": 0,
  "label": "Likely Human-Made",
  "confidence": "Low",
  "findings": [
    "short forensic finding"
  ],
  "reasoning_summary": "short forensic explanation"
}

Scoring guide:
0-24 = likely human-made or natural camera image
25-49 = mixed, edited, or suspicious
50-74 = likely synthetic or heavily digitally manipulated
75-100 = highly likely AI-generated

Look for:
- diffusion-style texture blending
- unnatural lighting gradients
- synthetic edges
- impossible anatomy or object structure
- over-smoothed surfaces
- hallucinated details
- neon/generated art style
- compositing artifacts
- screenshot or repost indicators
- missing provenance signals
"""
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{image_b64}",
                        },
                    ],
                }
            ],
        )

        data = json.loads(response.output_text.strip())

        score = data.get("ai_score", 0)

        return {
            "status": "complete",
            "score": score,
            "label": data.get("label", "Unknown"),
            "confidence": data.get("confidence", "Unknown"),
            "findings": data.get("findings", []),
            "reasoning_summary": data.get("reasoning_summary", ""),
            "raw": data,
        }

    except Exception as e:
        return {
            "status": "failed",
            "score": None,
            "label": str(e),
        }
