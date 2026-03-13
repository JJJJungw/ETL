import pandas as pd
import httpx
import os
import asyncio
import time
from bs4 import BeautifulSoup

AI_TEXT_SERVICE_URL = os.getenv("AI_SERVICE_URL")
AI_IMAGE_SERVICE_URL = os.getenv("AI_IMAGE_SERVICE_URL")


def clean_html(text):
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ", strip=True)


# -----------------------------
# 단일 기사 분석
# -----------------------------
async def analyze_one(client, article):

    try:

        # 텍스트 분석
        res = await client.post(
            AI_TEXT_SERVICE_URL,
            json={
                "title": article["title"],
                "content": article["raw_content"][:1000],
            },
            timeout=180.0,
        )

        data = res.json()

        article.update(
            {
                "summary": data.get("summary"),
                "sentiment": data.get("sentiment"),
                "category": data.get("category") or "기타",
            }
        )

        # 이미지 분석
        image_caption = None

        if article.get("image_url"):

            try:
                img_res = await client.post(
                    AI_IMAGE_SERVICE_URL,
                    json={"image_url": article["image_url"]},
                    timeout=180.0,
                )

                img_data = img_res.json()
                image_caption = img_data.get("caption")

            except Exception:
                image_caption = None

        article["image_caption"] = image_caption

    except Exception:

        article.update(
            {
                "summary": None,
                "sentiment": None,
                "category": "오류",
                "image_caption": None,
            }
        )

    return article


# -----------------------------
# 순차 처리
# -----------------------------
async def analyze_sequential(client, articles):

    results = []

    for article in articles:
        result = await analyze_one(client, article)
        results.append(result)

    return results


# -----------------------------
# 병렬 처리
# -----------------------------
async def analyze_concurrent(client, articles):

    tasks = [analyze_one(client, article) for article in articles]

    return await asyncio.gather(*tasks)


# -----------------------------
# transform + analyze
# -----------------------------
async def transform_and_analyze(news_list):

    if not news_list:
        return []

    # 전처리
    df = (
        pd.DataFrame(news_list)
        .drop_duplicates(subset=["url"])
        .dropna(subset=["raw_content"])
    )

    df["raw_content"] = df["raw_content"].apply(clean_html)

    df = df[df["raw_content"].str.len() > 20]

    # 30개 추출
    articles = [row.to_dict() for _, row in df.head(30).iterrows()]

    seq_articles = articles[:15]
    con_articles = articles[15:30]

    async with httpx.AsyncClient() as client:

        print(f"\n[Transform] 성능 비교 테스트 시작 (총 {len(articles)}건)")
        print(" 1~15 : 순차 처리")
        print("16~30 : 병렬 처리")

        # -----------------------------
        # 순차 처리
        # -----------------------------
        start_seq = time.perf_counter()

        seq_results = await analyze_sequential(client, seq_articles)

        end_seq = time.perf_counter()

        seq_time = end_seq - start_seq

        # -----------------------------
        # 병렬 처리
        # -----------------------------
        start_con = time.perf_counter()

        con_results = await analyze_concurrent(client, con_articles)

        end_con = time.perf_counter()

        con_time = end_con - start_con

        # -----------------------------
        # 결과 리포트
        # -----------------------------
        print("\n" + "=" * 50)
        print("[성능 비교 결과]")
        print(f"순차 처리 (15건): {seq_time:.2f}초")
        print(f"병렬 처리 (15건): {con_time:.2f}초")
        print(f"속도 개선율: {((seq_time - con_time) / seq_time * 100):.1f}%")
        print("=" * 50 + "\n")

    # 결과 합치기 (총 30개)
    results = seq_results + con_results

    return results