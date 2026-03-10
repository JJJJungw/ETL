import pandas as pd
import httpx
import os
import asyncio
from bs4 import BeautifulSoup

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL")

def clean_html(text):
    """BeautifulSoup을 사용해 HTML 태그를 제거합니다."""
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ", strip=True)

async def transform_and_analyze(news_list):
    """뉴스 리스트를 받아 정제 후 AI 분석 결과를 추가합니다."""
    if not news_list:
        return []

    # 1. pandas로 중복 URL 제거 및 본문 정제
    df = pd.DataFrame(news_list)
    df = df.drop_duplicates(subset=['url'])
    df['raw_content'] = df['raw_content'].apply(clean_html)
    
    transformed_data = []
    
    # 2. httpx 비동기 클라이언트로 AI 서버 호출
    async with httpx.AsyncClient(timeout=60.0) as client:
        for _, row in df.iterrows():
            summary, sentiment = None, None
            try:
                # AI 서버(8001)에 분석 요청
                response = await client.post(
                    AI_SERVICE_URL,
                    json={
                        "title": row['title'],
                        "content": row['raw_content'][:1000] # 모델 입력 제한 고려
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    summary = data.get("summary")
                    sentiment = data.get("sentiment")
                else:
                    print(f" AI 서버 응답 이상: {response.status_code}")
            except Exception as e:
                print(f" AI 분석 호출 실패 ({row['url']}): {e}")
            
            # 결과 합치기
            article = row.to_dict()
            article.update({
                "summary": summary,
                "sentiment": sentiment
            })
            transformed_data.append(article)
            
    return transformed_data