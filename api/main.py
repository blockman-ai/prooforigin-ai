from fastapi import FastAPI

app = FastAPI(title="ProofOrigin AI API")

@app.get("/")
def root():
    return {
        "name": "ProofOrigin AI",
        "status": "running",
        "mission": "Media authenticity research and model evaluation"
    }
