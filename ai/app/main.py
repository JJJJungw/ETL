import os
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline

app = FastAPI()

# 1. 환경변수 로드 (.env 및 docker-compose에서 주입된 값)
CACHE_DIR = os.getenv("TRANSFORMERS_CACHE", "/models")
SUM_MODEL = os.getenv("SUMMARIZATION_MODEL")
SEN_MODEL = os.getenv("SENTIMENT_MODEL")

MODELS = {}

@app.on_event("startup")
async def load_models():
    # 환경변수 설정 누락 여부 확인
    if not SUM_MODEL or not SEN_MODEL:
        print(" 에러: 환경변수(SUMMARIZATION_MODEL, SENTIMENT_MODEL)가 설정되지 않았습니다.")
        return

    print(f"📦 모델 로딩 시작 (Cache: {CACHE_DIR})...")
    print(f" - 요약 모델: {SUM_MODEL}")
    print(f" - 감성 모델: {SEN_MODEL}")
    
    try:
        # 2. 요약 모델 로드
        MODELS["summarizer"] = pipeline(
            "summarization", 
            model=SUM_MODEL,
            model_kwargs={"cache_dir": CACHE_DIR}
        )
        # 3. 감성 분석 모델 로드
        MODELS["sentiment"] = pipeline(
            "text-classification", 
            model=SEN_MODEL,
            model_kwargs={"cache_dir": CACHE_DIR}
        )
        print(" 모든 AI 모델이 성공적으로 로드되었습니다!")
    except Exception as e:
        print(f" 모델 로드 실패: {str(e)}")

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
        content = request.content.strip()
        
        # [방어 로직] 입력이 너무 짧으면 요약할 필요가 없으므로 그냥 원문을 씁니다.
        # 보통 50자 미만은 요약하면 오히려 망가집니다.
        if len(content) < 50:
            summary_text = content
        else:
            summary_res = MODELS["summarizer"](
                content[:512], 
                max_length=50,
                min_length=10,
                do_sample=False, 
                no_repeat_ngram_size=3,
                repetition_penalty=2.5 # 페널티를 조금 더 강화(2.0 -> 2.5)
            )
            summary_text = summary_res[0]['summary_text']
        
        # 감성 분석 (이건 짧아도 잘 작동합니다)
        sentiment_input = f"{request.title} {content}"[:512]
        sentiment_res = MODELS["sentiment"](sentiment_input)[0]
        
        return {
            "summary": summary_text,
            "sentiment": sentiment_res['label'].lower()
        }
    except Exception as e:
        print(f" Analysis error: {str(e)}")
        return {"summary": None, "sentiment": None, "error": "analysis_failed"}