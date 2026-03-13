import asyncio
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.extract import extract_all_sections
from app.transform import transform_and_analyze
from app.load import load_to_db
from app.database import engine, Base, init_db
from app.report import generate_daily_report

async def run_etl():
    """실제 RSS 데이터를 긁어와서 분석하고 DB에 저장하는 ETL 파이프라인"""
    print("\n" + "="*50)
    print(f"  [ETL START] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. Extract (이미지 URL 추출 로직이 포함된 extract_all_sections 호출)
        print("  [Step 1] RSS 뉴스 섹션별 수집 중 (이미지 포함)...")
        raw_news_data = await extract_all_sections() 
        
        if not raw_news_data:
            print("  수집된 뉴스 데이터가 없습니다. 다음 턴에 재시도합니다.")
            return

        # 2. Transform & Analyze (텍스트 분석 및 이미지 캡셔닝 통합 처리)
        # 여기서 transform_and_analyze 내부적으로 /analyze와 /analyze/image를 적절히 호출하게 됨
        print(f"  [Step 2] 데이터 정제 및 AI 분석 시작 (총 {len(raw_news_data)}건)...")
        analyzed_results = await transform_and_analyze(raw_news_data)
        
        # 로그 출력 시 이미지 분석 여부도 살짝 보여주면 좋겠죠?
        for res in analyzed_results[:3]:
            has_img = "O" if res.get('image_caption') else "X"
            print(
            f" [분석완료] {res['title'][:20]}... | "
            f"카테고리: {res.get('category')} | "
            f"이미지분석: {has_img}"
        )

        # 3. Load (DB 적재 - image_description 컬럼이 추가된 상태여야 함)
        print(f"  [Step 3] DB(PostgreSQL) 적재 시작 ({len(analyzed_results)}건)...")
        await load_to_db(analyzed_results)
        
    except Exception as e:
        print(f"  ETL 프로세스 중 에러 발생: {e}")
        import traceback
        traceback.print_exc() # 상세 에러 추적을 위해 추가
    
    print(f" ✨ [ETL END] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50 + "\n")

async def main():
    """APScheduler를 활용한 서비스 제어"""
    print("  Collector 서비스 스케줄러를 준비 중입니다")
    
    # 1. DB 초기화 (테이블 생성)
    await init_db()
    
    # 2. 스케줄러 설정
    scheduler = AsyncIOScheduler()
    
    # [기존] 1시간마다 뉴스 수집 ETL 실행
    scheduler.add_job(
        run_etl,
        'interval',
        minutes=5,  # 5분마다 실행
        next_run_time=datetime.datetime.now(),  # 컨테이너 시작 시 바로 1회 실행
        id='news_etl_job'
    )
    
    # [과제 2-A] 운영용: 매일 자정 (어제 데이터 집계)
    scheduler.add_job(
        generate_daily_report, 
        'cron', 
        hour=0, 
        minute=0, 
        args=[False], 
        id='daily_report_job'
    )
    
    # [과제 2-B] 테스트용: 현재 시간 기준 1분 뒤에 리포트 생성 실행
    test_run_time = datetime.datetime.now() + datetime.timedelta(minutes=1)
    scheduler.add_job(
        generate_daily_report, 
        'date', 
        run_date=test_run_time, 
        args=[True], 
        id='test_report_job'
    )
    
    scheduler.start()
    print(f"  스케줄러 시작 완료!")
    print(f"  - 뉴스 수집: 1시간 주기")
    print(f"  - 자정 리포트: 매일 00:00")
    print(f"  - 테스트 리포트 예약: {test_run_time.strftime('%H:%M:%S')} (1분 뒤)")

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("  Collector 서비스를 종료합니다.")

if __name__ == "__main__":
    asyncio.run(main())