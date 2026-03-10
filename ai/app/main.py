import os
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline

app = FastAPI()

# 1. 환경변수 로드
CACHE_DIR = os.getenv("TRANSFORMERS_CACHE", "/models")
SUM_MODEL = os.getenv("SUMMARIZATION_MODEL")
SEN_MODEL = os.getenv("SENTIMENT_MODEL")

MODELS = {}

@app.on_event("startup")
async def load_models():
    if not SUM_MODEL or not SEN_MODEL:
        print(" 에러: 환경변수 설정 누락")
        return

    print(f"모델 로딩 시작: {SEN_MODEL}")
    
    try:
        # 요약 모델 로드
        MODELS["summarizer"] = pipeline(
            "summarization", 
            model=SUM_MODEL,
            model_kwargs={"cache_dir": CACHE_DIR}
        )
        # 감성 분석 모델 로드 (lxyuan 모델 최적화)
        MODELS["sentiment"] = pipeline(
            "text-classification", 
            model=SEN_MODEL,
            model_kwargs={"cache_dir": CACHE_DIR}
        )
        print(" 모든 AI 모델 로드 완료!")
    except Exception as e:
        print(f" 모델 로드 실패: {str(e)}")

@app.get("/health")
def health():
    is_ready = "summarizer" in MODELS and "sentiment" in MODELS
    return {"status": "ok" if is_ready else "loading", "model_loaded": is_ready}

class AnalyzeRequest(BaseModel):
    title: str
    content: str

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    if not MODELS:
        return {"summary": None, "sentiment": None, "error": "Models not ready"}

    try:
        # 전처리: 불필요한 공백 제거
        clean_content = " ".join(request.content.split())
        
        # [1] 요약 로직 (2~3문장 타겟)
        if len(clean_content) < 60:
            summary_text = clean_content
        else:
            summary_res = MODELS["summarizer"](
                clean_content[:1024], 
                max_length=80,      # 2~3문장이 나오려면 60~80 정도가 적당합니다
                min_length=30,      # 너무 짧으면 문장이 끊깁니다
                do_sample=False, 
                no_repeat_ngram_size=3, # 3개 단어 반복 시 차단 (2는 너무 빡빡할 수 있음)
                repetition_penalty=2.5,  # 5.0은 문장이 망가질 수 있어 2.5로 조정
                length_penalty=1.0, 
                num_beams=4
            )
            summary_text = summary_res[0]['summary_text']

        # [2] 감성 분석 로직 (lxyuan 모델 전용)
        # 제목과 본문을 합쳐 문맥 파악 극대화
        sentiment_input = f"{request.title} {clean_content}"[:512]
        sentiment_res = MODELS["sentiment"](sentiment_input)[0]
        
        # 모델이 'POSITIVE', 'NEGATIVE', 'NEUTRAL'을 주므로 소문자로 통일
        sentiment_label = sentiment_res['label'].lower()
        
        # [검증] 혹리 모델이 의도치 않은 레이블을 줄 경우를 대비한 방어 로직
        valid_labels = ["positive", "negative", "neutral"]
        if sentiment_label not in valid_labels:
            sentiment_label = "neutral"

        return {
            "summary": summary_text.strip(),
            "sentiment": sentiment_label
        }
        
    except Exception as e:
        print(f" 분석 에러: {str(e)}")
        return {"summary": None, "sentiment": "neutral", "error": "analysis_failed"}