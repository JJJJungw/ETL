import asyncio
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler # 추가
from app.extract import extract_all_sections
from app.transform import transform_and_analyze
from app.load import load_to_db
from app.database import engine, Base

async def init_db():
    """애플리케이션 시작 시 테이블 자동 생성"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("  [DB] 데이터베이스 테이블 확인/생성 완료")
    except Exception as e:
        print(f"  [DB] 초기화 중 에러 발생: {e}")

async def run_etl():
    """실제 RSS 데이터를 긁어와서 분석하고 DB에 저장하는 ETL 파이프라인"""
    print("\n" + "="*50)
    print(f"  [ETL START] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. Extract
        print("  [Step 1] RSS 뉴스 섹션별 수집 중...")
        raw_news_data = await extract_all_sections() 
        
        if not raw_news_data:
            print("  수집된 뉴스 데이터가 없습니다. 다음 턴에 재시도합니다.")
            return

        # 2. Transform & Analyze
        print(f"  [Step 2] 데이터 정제 및 AI 분석 시작 (총 {len(raw_news_data)}건)...")
        analyzed_results = await transform_and_analyze(raw_news_data)
        
        for res in analyzed_results[:3]:
            print(f" [분석완료] {res['title'][:25]}... | 감성: {res['sentiment']}")

        # 3. Load
        print(f"  [Step 3] DB(PostgreSQL) 적재 시작 ({len(analyzed_results)}건)...")
        await load_to_db(analyzed_results)
        
    except Exception as e:
        print(f"  ETL 프로세스 중 에러 발생: {e}")
    
    print(f" ✨ [ETL END] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50 + "\n")

async def main():
    """APScheduler를 활용한 서비스 제어"""
    print("  Collector 서비스 스케줄러를 준비 중입니다")
    
    # 1. DB 초기화 (테이블 생성)
    await init_db()
    
    # 2. 스케줄러 설정
    scheduler = AsyncIOScheduler()
    
    # [과제 요건] 1시간마다 실행하도록 설정
    # 'interval' 방식을 사용하여 hours=1로 설정합니다.
    scheduler.add_job(run_etl, 'interval', hours=1, next_run_time=datetime.datetime.now())
    
    scheduler.start()
    print("  스케줄러가 시작되었습니다. (주기: 1시간, 첫 실행: 즉시)")

    # 서비스가 종료되지 않도록 무한 루프 유지
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("  Collector 서비스를 종료합니다.")

if __name__ == "__main__":
    asyncio.run(main())