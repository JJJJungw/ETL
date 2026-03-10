import asyncio
import datetime
from app.extract import extract_all_sections  # 구글 뉴스 RSS 수집
from app.transform import transform_and_analyze # AI 분석
from app.load import load_to_db  # PostgreSQL 적재 (Upsert)
from app.database import engine, Base # DB 엔진 및 모델 메타데이터

async def init_db():
    """애플리케이션 시작 시 테이블 자동 생성 (JPA ddl-auto=update 효과)"""
    try:
        async with engine.begin() as conn:
            # 모델(Base)에 정의된 모든 테이블을 생성합니다.
            await conn.run_sync(Base.metadata.create_all)
        print("✅ [DB] 데이터베이스 테이블 확인/생성 완료")
    except Exception as e:
        print(f"❌ [DB] 초기화 중 에러 발생: {e}")

async def run_etl():
    """실제 RSS 데이터를 긁어와서 분석하고 DB에 저장하는 ETL 파이프라인"""
    print("\n" + "="*50)
    print(f"🚀 [ETL START] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. Extract (구글 뉴스 RSS 순회 크롤링)
        print("📥 [Step 1] RSS 뉴스 섹션별 수집 중...")
        raw_news_data = await extract_all_sections() 
        
        if not raw_news_data:
            print("⚠️ 수집된 뉴스 데이터가 없습니다. 다음 턴에 재시도합니다.")
            return

        # 2. Transform & Analyze (데이터 정제 + AI 분석)
        print(f"🧠 [Step 2] 데이터 정제 및 AI 분석 시작 (총 {len(raw_news_data)}건)...")
        analyzed_results = await transform_and_analyze(raw_news_data)
        
        # 동작 확인용 상위 3건만 로그 출력
        for res in analyzed_results[:3]:
            print(f"   ✅ [분석완료] {res['title'][:25]}... | 감성: {res['sentiment']}")

        # 3. Load (DB 적재 - SQLAlchemy 2.0 Upsert)
        print(f"💾 [Step 3] DB(PostgreSQL) 적재 시작 ({len(analyzed_results)}건)...")
        await load_to_db(analyzed_results)
        
    except Exception as e:
        print(f"❌ ETL 프로세스 중 에러 발생: {e}")
    
    print(f"✨ [ETL END] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50 + "\n")

async def main():
    """스케줄러: 서비스 시작 즉시 실행 후 1시간 주기로 반복"""
    print("🚀 Collector 서비스가 정상적으로 시작되었습니다.")
    
    # 1. 시작하자마자 DB 테이블부터 세팅 (JPA의 자동 생성 기능처럼!)
    await init_db()
    
    while True:
        try:
            # 2. ETL 파이프라인 가동
            await run_etl()
            
            # 3. 1시간(3600초) 대기
            next_run = datetime.datetime.now() + datetime.timedelta(hours=1)
            print(f"💤 다음 실행 예정 시각: {next_run.strftime('%H:%M:%S')}")
            await asyncio.sleep(3600) 
            
        except Exception as e:
            print(f"❗ 메인 루프 실행 중 치명적 에러 발생: {e}")
            await asyncio.sleep(60)  # 에러 시 1분 휴식 후 재시도

if __name__ == "__main__":
    asyncio.run(main())