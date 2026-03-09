import asyncio
import os
from app.transform import transform_and_analyze

async def run_etl():
    """1회성 ETL 프로세스 실행"""
    print("\n" + "="*50)
    print(" ETL 파이프라인 가동 시작...")
    
    # 1. Extract (나중에 RSS 크롤링 로직이 들어올 자리)
    print(" [Step 1] 데이터 추출 중...")
    sample_news = [
        {
            "title": "삼성전자 주가 분석",
            "url": "https://news.example.com/1",
            "raw_content": "<b>삼성전자</b>의 반도체 실적이 개선되며 주가가 상승세를 보이고 있습니다."
        },
        {
            "title": "네이버 신규 서비스 런칭",
            "url": "https://news.example.com/2",
            "raw_content": "네이버가 새로운 AI 서비스를 공개했습니다."
        }
    ]

    # 2. Transform & Analyze
    print(" [Step 2] 데이터 정제 및 AI 분석 진행 중...")
    analyzed_results = await transform_and_analyze(sample_news)
    
    for res in analyzed_results:
        print(f"   - [분석완료] {res['title'][:20]}... | 요약: {res['summary']} | 감성: {res['sentiment']}")

    # 3. Load (나중에 DB 저장 로직이 들어올 자리)
    print(" [Step 3] DB 적재 준비 중 (Coming Soon)")
    print("="*50 + "\n")

async def main():
    """무한 루프를 돌며 스케줄링 수행"""
    print("✅ Collector 서비스가 정상적으로 시작되었습니다.")
    
    while True:
        try:
            await run_etl()
            print(" 다음 실행까지 1시간 대기합니다...")
            await asyncio.sleep(3600)  # 1시간 대기
        except Exception as e:
            print(f" 루프 실행 중 치명적 에러 발생: {e}")
            await asyncio.sleep(60)  # 에러 시 1분 후 재시도

if __name__ == "__main__":
    # 도커 환경에서 프로세스가 바로 종료되지 않도록 이벤트 루프 실행
    asyncio.run(main())