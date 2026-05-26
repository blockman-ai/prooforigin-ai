import requests
import os


SIGHTENGINE_USER = os.getenv("SIGHTENGINE_USER")
SIGHTENGINE_SECRET = os.getenv("SIGHTENGINE_SECRET")


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

        ai_score = (
            data.get("type", {})
            .get("ai_generated", 0)
        )

        score_percent = round(ai_score * 100)

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
