import os
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline

app = FastAPI()

CACHE_DIR = os.getenv("TRANSFORMERS_CACHE", "/models")
MODELS = {}

@app.on_event("startup")
async def load_models():
    print(f" Loading models into {CACHE_DIR}...")
    try:
        MODELS["summarizer"] = pipeline(
            "summarization", 
            model="digit82/kobart-summarization",
            model_kwargs={"cache_dir": CACHE_DIR}
        )
        MODELS["sentiment"] = pipeline(
            "text-classification", 
            model="snunlp/KR-FinBert-SC",
            model_kwargs={"cache_dir": CACHE_DIR}
        )
        print("All AI models loaded successfully!")
    except Exception as e:
        print(f" Failed to load models: {str(e)}")

@app.get("/health")
def health():
    is_ready = "summarizer" in MODELS and "sentiment" in MODELS
    return {
        "status": "ok" if is_ready else "loading", 
        "model_loaded": is_ready
    }

class AnalyzeRequest(BaseModel):
    title: str
    content: str

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    if not MODELS:
        return {"summary": None, "sentiment": None, "error": "Models not ready"}

    try:
        summary_res = MODELS["summarizer"](
            request.content[:512], 
            max_length=100, 
            min_length=30,
            do_sample=False
        )
        summary_text = summary_res[0]['summary_text']
        
        sentiment_input = f"{request.title} {request.content}"[:512]
        sentiment_res = MODELS["sentiment"](sentiment_input)[0]
        
        return {
            "summary": summary_text,
            "sentiment": sentiment_res['label'].lower()
        }
    except Exception as e:
        print(f" Analysis error: {str(e)}")
        return {"summary": None, "sentiment": None, "error": "analysis_failed"}