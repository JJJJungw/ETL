import datetime
from collections import Counter
from kiwipiepy import Kiwi
from sqlalchemy import select, func
from .database import SessionLocal  # database.py의 변수명에 맞춰 수정 완료
from .models import Article, Report

# 형태소 분석기 초기화
kiwi = Kiwi()

async def generate_daily_report(is_test: bool = True):
    """
    일간 뉴스 수집 현황 리포트 생성 함수
    is_test=True: 오늘 수집된 데이터를 즉시 집계 (테스트용)
    is_test=False: 어제 수집된 데이터를 집계 (운영용)
    """
    # database.py에서 정의한 비동기 세션 생성기(SessionLocal) 사용
    async with SessionLocal() as db:
        try:
            # 1. 날짜 범위 설정
            today = datetime.date.today()
            target_date = today if is_test else today - datetime.timedelta(days=1)
            next_day = target_date + datetime.timedelta(days=1)
            
            print(f"  [Report] {target_date} 데이터 분석 시작 (모드: {'테스트' if is_test else '운영'})")

            # 2. 대상 기사 데이터 쿼리 (비동기)
            # collected_at은 datetime 타입이므로 날짜 범위로 조회
            query = select(Article).where(
                Article.collected_at >= target_date,
                Article.collected_at < next_day
            )
            result = await db.execute(query)
            articles = result.scalars().all()

            total_count = len(articles)
            if total_count == 0:
                print(f"  [Report] {target_date} 자에 수집된 기사가 없어 리포트를 생성하지 않습니다.")
                return

            # 3. 통계 계산 (감성 비율 및 성공률)
            sentiments = [a.sentiment for a in articles if a.sentiment]
            # summary가 존재하면 AI 분석 성공으로 간주
            success_count = len([a for a in articles if a.summary is not None])
            
            def calc_percent(count, total):
                return round((count / total) * 100, 1) if total > 0 else 0.0

            pos_p = calc_percent(sentiments.count("positive"), total_count)
            neg_p = calc_percent(sentiments.count("negative"), total_count)
            neu_p = calc_percent(sentiments.count("neutral"), total_count)
            success_rate = calc_percent(success_count, total_count)

            # 4. 키워드 추출 (제목 데이터 활용)
            all_titles = " ".join([a.title for a in articles])
            tokens = kiwi.tokenize(all_titles)
            
            # 일반명사(NNG), 고유명사(NNP) 중 2글자 이상만 추출
            nouns = [
                t.form for t in tokens 
                if t.tag in ['NNG', 'NNP'] and len(t.form) > 1
            ]
            top_5_list = [word for word, count in Counter(nouns).most_common(5)]
            top_keywords_str = ",".join(top_5_list)

            # 5. DB 저장 (Upsert 로직: 이미 해당 날짜 리포트가 있으면 업데이트)
            report_query = select(Report).where(Report.target_date == target_date)
            report_result = await db.execute(report_query)
            existing_report = report_result.scalar_one_or_none()

            if existing_report:
                existing_report.total_count = total_count
                existing_report.pos_ratio = pos_p
                existing_report.neg_ratio = neg_p
                existing_report.neu_ratio = neu_p
                existing_report.success_rate = success_rate
                existing_report.top_keywords = top_keywords_str
                print(f"  [Report] {target_date} 기존 리포트를 업데이트합니다.")
            else:
                new_report = Report(
                    target_date=target_date,
                    total_count=total_count,
                    pos_ratio=pos_p,
                    neg_ratio=neg_p,
                    neu_ratio=neu_p,
                    success_rate=success_rate,
                    top_keywords=top_keywords_str
                )
                db.add(new_report)

            await db.commit()
            print(f" ✨ [Report] {target_date} 리포트 생성 완료! (키워드: {top_keywords_str})")

        except Exception as e:
            print(f" ❌ [Report] 실행 중 에러 발생: {e}")
            await db.rollback()