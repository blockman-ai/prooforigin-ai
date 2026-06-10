import base64
import json
import os
import requests
from openai import OpenAI

SIGHTENGINE_USER = os.getenv("SIGHTENGINE_USER")
SIGHTENGINE_SECRET = os.getenv("SIGHTENGINE_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

ENGINE_TIMEOUT_SECONDS = int(os.getenv("PROOFORIGIN_ENGINE_TIMEOUT_SECONDS", "60"))

openai_client = (
    OpenAI(api_key=OPENAI_API_KEY, timeout=ENGINE_TIMEOUT_SECONDS)
    if OPENAI_API_KEY
    else None
)


def _sightengine_unavailable(message):
    return {
        "status": "failed",
        "score": None,
        "label": message,
    }


def _openai_unavailable(message):
    return {
        "status": "failed",
        "score": None,
        "label": message,
    }


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
                timeout=ENGINE_TIMEOUT_SECONDS,
            )

        if response.status_code >= 500:
            return _sightengine_unavailable("Sightengine service unavailable")

        data = response.json()

        if response.status_code >= 400 or data.get("error"):
            error_message = data.get("error", {}).get("message", "Sightengine request failed")
            return _sightengine_unavailable(str(error_message))

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
        }

    except requests.Timeout:
        return _sightengine_unavailable("Sightengine request timed out")
    except requests.RequestException as e:
        return _sightengine_unavailable(f"Sightengine request failed: {e}")
    except (ValueError, TypeError, KeyError) as e:
        return _sightengine_unavailable(f"Sightengine response parsing failed: {e}")
    except Exception as e:
        return _sightengine_unavailable(str(e))


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

        raw_text = getattr(response, "output_text", "") or ""
        raw_text = raw_text.strip()

        if not raw_text:
            return _openai_unavailable("Empty OpenAI response")

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            return {
                "status": "failed",
                "score": None,
                "label": "Parsing Failure",
                "details": raw_text[:300],
            }

        score = data.get("ai_score", 0)

        return {
            "status": "complete",
            "score": score,
            "label": data.get("label", "Unknown"),
            "confidence": data.get("confidence", "Unknown"),
            "findings": data.get("findings", []),
            "reasoning_summary": data.get("reasoning_summary", ""),
        }

    except TimeoutError:
        return _openai_unavailable("OpenAI request timed out")
    except Exception as e:
        error_name = type(e).__name__
        if "timeout" in error_name.lower() or "timeout" in str(e).lower():
            return _openai_unavailable("OpenAI request timed out")
        return _openai_unavailable(str(e))
