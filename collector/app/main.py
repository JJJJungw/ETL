import asyncio
import os
import datetime
from app.extract import extract_all_sections  # 새로 만든 크롤링 함수
from app.transform import transform_and_analyze
# from app.load import load_to_db  <-- 다음 스텝에서 추가할 DB 저장 로직

async def run_etl():
    """실제 RSS 데이터를 긁어와서 분석하는 ETL 파이프라인"""
    print("\n" + "="*50)
    print(f" [ETL START] {datetime.datetime.now()}")
    
    try:
        # 1. Extract (6대 섹션 순회 크롤링)
        print(" [Step 1] 네이버 뉴스 RSS 섹션별 추출 중...")
        raw_news_data = await extract_all_sections() 
        
        if not raw_news_data:
            print(" 수집된 뉴스 데이터가 없습니다. 다음 턴에 재시도합니다.")
            return

        # 2. Transform & Analyze (pandas 정제 + AI 분석)
        print(f"[Step 2] 데이터 정제 및 AI 분석 시작 (총 {len(raw_news_data)}건)...")
        # 명세서 요건: 기사 1건씩 순차 처리 (transform_and_analyze 내부 로직 확인 필요)
        analyzed_results = await transform_and_analyze(raw_news_data)
        
        # 동작 확인용 상위 3건 출력
        for res in analyzed_results[:3]:
            print(f" [분석완료] {res['title'][:20]}... | 감성: {res['sentiment']}")

        # 3. Load (DB 적재 - 다음 단계에서 완성 예정)
        print(f" [Step 3] DB 적재 준비 중 ({len(analyzed_results)}건)")
        # await load_to_db(analyzed_results)
        
    except Exception as e:
        print(f" ETL 프로세스 중 에러 발생: {e}")
    
    print(f" [ETL END] {datetime.datetime.now()}")
    print("="*50 + "\n")

async def main():
    """스케줄러: 컨테이너 시작 즉시 실행 후 1시간 주기로 반복"""
    print(" Collector 서비스가 정상적으로 시작되었습니다.")
    
    while True:
        try:
            # 요구사항: 컨테이너 시작 즉시 & 매 시간 실행
            await run_etl()
            
            # 요구사항: 1시간(3600초) 대기
            print(f" 다음 실행 시각: {datetime.datetime.now() + datetime.timedelta(hours=1)}")
            await asyncio.sleep(3600) 
            
        except Exception as e:
            print(f" 메인 루프 실행 중 치명적 에러 발생: {e}")
            await asyncio.sleep(60)  # 치명적 에러 시 1분 휴식 후 재시도

if __name__ == "__main__":
    asyncio.run(main())