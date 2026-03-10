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
            # [수정] 기본값을 None 대신 설정해줍니다.
            summary = "분석 대기 중" 
            sentiment = "unknown"
            
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
                    # [수정] AI 응답이 있어도 내용이 비어있을 경우를 대비합니다.
                    summary = data.get("summary") or "분석 결과가 비어있습니다."
                    sentiment = data.get("sentiment") or "unknown"
                else:
                    # [수정] 403, 500 등 서버 응답 에러 시 메시지
                    print(f" AI 서버 응답 이상: {response.status_code}")
                    summary = "민감한 내용 포함으로 AI 분석이 제한되었습니다."
                    sentiment = "unknown"

            except Exception as e:
                # [수정] 네트워크 에러나 타임아웃 등 예외 발생 시 메시지
                print(f" AI 분석 호출 실패 ({row['url']}): {e}")
                summary = "AI 서비스 호출 실패로 분석을 완료하지 못했습니다."
                sentiment = "error"
            
            # 결과 합치기
            article = row.to_dict()
            article.update({
                "summary": summary,
                "sentiment": sentiment
            })
            transformed_data.append(article)
            
    return transformed_data