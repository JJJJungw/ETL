import os
import ssl
import torch
import requests
import urllib3
import subprocess
import tempfile
from io import BytesIO
from PIL import Image
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline, BlipProcessor, BlipForConditionalGeneration
from sentence_transformers import SentenceTransformer, util
from requests.adapters import HTTPAdapter


# -------------------------------------------------
# SSL workaround
# -------------------------------------------------

class TLSAdapter(HTTPAdapter):

    def init_poolmanager(self, *args, **kwargs):

        ctx = ssl.create_default_context()
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")

        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        kwargs["ssl_context"] = ctx

        return super().init_poolmanager(*args, **kwargs)


session = requests.Session()
session.mount("https://", TLSAdapter())

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# -------------------------------------------------
# 전역 설정
# -------------------------------------------------

MODELS = {}

CANDIDATE_LABELS = [
    "정치",
    "경제",
    "사회",
    "지역",
    "문화",
    "세계",
    "IT/과학"
]


# -------------------------------------------------
# 이미지 다운로드 함수
# -------------------------------------------------

def download_image(url: str):

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = session.get(url, timeout=10, headers=headers)
        response.raise_for_status()

        return Image.open(BytesIO(response.content)).convert("RGB")

    except Exception:

        print("requests 실패 → curl fallback")

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            path = tmp.name

        cmd = [
            "curl",
            "-L",
            "-k",
            "-A",
            "Mozilla/5.0",
            "-o",
            path,
            url
        ]

        subprocess.run(cmd, check=True)

        return Image.open(path).convert("RGB")


# -------------------------------------------------
# FastAPI Lifespan
# -------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    print("\n" + "=" * 50)
    print("[Startup] AI 모델 로딩 시작")

    CACHE_DIR = os.getenv("TRANSFORMERS_CACHE", "/models")

    SUM_MODEL = os.getenv(
        "SUMMARIZATION_MODEL",
        "digit82/kobart-summarization"
    )

    SEN_MODEL = os.getenv(
        "SENTIMENT_MODEL",
        "lxyuan/distilbert-base-multilingual-cased-sentiments-student"
    )

    CAT_MODEL = os.getenv(
        "CATEGORY_MODEL",
        "jhgan/ko-sroberta-multitask"
    )

    IMG_MODEL = os.getenv(
        "IMAGE_CAPTION_MODEL",
        "Salesforce/blip-image-captioning-base"
    )

    device = 0 if torch.cuda.is_available() else -1

    try:

        MODELS["summarizer"] = pipeline(
            "summarization",
            model=SUM_MODEL,
            device=device,
            model_kwargs={"cache_dir": CACHE_DIR}
        )

        MODELS["sentiment"] = pipeline(
            "text-classification",
            model=SEN_MODEL,
            device=device,
            model_kwargs={"cache_dir": CACHE_DIR}
        )

        MODELS["classifier"] = SentenceTransformer(
            CAT_MODEL,
            cache_folder=CACHE_DIR
        )

        MODELS["label_embeddings"] = MODELS["classifier"].encode(
            CANDIDATE_LABELS,
            convert_to_tensor=True
        )

        print(f"[Image Model] loading {IMG_MODEL}")

        MODELS["image_processor"] = BlipProcessor.from_pretrained(
            IMG_MODEL,
            cache_dir=CACHE_DIR
        )

        MODELS["image_model"] = BlipForConditionalGeneration.from_pretrained(
            IMG_MODEL,
            cache_dir=CACHE_DIR
        )

        if torch.cuda.is_available():
            MODELS["image_model"].to("cuda")

        print("[Success] 모델 로딩 완료")

    except Exception as e:
        print("모델 로딩 실패:", e)
        raise e

    print("=" * 50 + "\n")

    yield

    print("[Shutdown] 모델 메모리 해제")
    MODELS.clear()


app = FastAPI(lifespan=lifespan)


# -------------------------------------------------
# Request Models
# -------------------------------------------------

class AnalyzeRequest(BaseModel):
    title: str
    content: str


class ImageAnalyzeRequest(BaseModel):
    image_url: str


# -------------------------------------------------
# health check
# -------------------------------------------------

@app.get("/health")
def health():

    required = [
        "summarizer",
        "sentiment",
        "classifier",
        "image_model"
    ]

    ready = all(k in MODELS for k in required)

    return {
        "status": "ok" if ready else "loading",
        "model_loaded": ready
    }


# -------------------------------------------------
# text analysis
# -------------------------------------------------

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):

    if not MODELS:
        return {
            "summary": None,
            "sentiment": "neutral",
            "category": "기타"
        }

    try:

        clean_content = " ".join(request.content.split())

        if len(clean_content) < 60:
            summary_text = clean_content
        else:

            summary_res = MODELS["summarizer"](
                clean_content[:1024],
                max_new_tokens=80,
                num_beams=4,
                repetition_penalty=2.5,
                do_sample=False
            )

            summary_text = summary_res[0]["summary_text"]

        sentiment_input = f"{request.title} {clean_content[:200]}"[:512]

        sentiment_res = MODELS["sentiment"](sentiment_input)[0]

        raw_label = sentiment_res["label"].lower()
        raw_score = sentiment_res["score"]

        if "neg" in raw_label and raw_score > 0.4:
            sentiment_label = "negative"

        elif "pos" in raw_label and raw_score > 0.7:
            sentiment_label = "positive"

        else:
            sentiment_label = "neutral"

        embedding = MODELS["classifier"].encode(
            request.title,
            convert_to_tensor=True
        )

        scores = util.cos_sim(
            embedding,
            MODELS["label_embeddings"]
        )[0]

        category = CANDIDATE_LABELS[
            torch.argmax(scores).item()
        ]

        return {
            "summary": summary_text.strip(),
            "sentiment": sentiment_label,
            "category": category,
            "debug": {
                "raw_label": raw_label,
                "score": round(raw_score, 4)
            }
        }

    except Exception as e:

        print("Text analysis error:", e)

        return {
            "summary": None,
            "sentiment": "neutral",
            "category": "기타",
            "error": str(e)
        }


# -------------------------------------------------
# image caption
# -------------------------------------------------

@app.post("/analyze/image")
async def analyze_image(request: ImageAnalyzeRequest):

    if "image_model" not in MODELS:
        return {
            "caption": None,
            "error": "Image model not loaded"
        }

    try:

        raw_image = download_image(request.image_url)

        inputs = MODELS["image_processor"](
            raw_image,
            return_tensors="pt"
        )

        if torch.cuda.is_available():
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        out = MODELS["image_model"].generate(
            **inputs,
            max_new_tokens=40
        )

        caption = MODELS["image_processor"].decode(
            out[0],
            skip_special_tokens=True
        )

        return {
            "caption": caption.strip(),
            "status": "success"
        }

    except Exception as e:

        print("Image analysis error:", e)

        return {
            "caption": None,
            "error": str(e)
        }