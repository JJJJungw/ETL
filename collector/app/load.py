# collector/app/load.py
from sqlalchemy.dialects.postgresql import insert
from app.database import SessionLocal
from app.models import Article

async def load_to_db(articles_data: list[dict]):
    """
    데이터를 DB에 적재합니다. URL이 중복되면 summary와 sentiment만 업데이트합니다.
    """
    if not articles_data:
        return

    async with SessionLocal() as session:
        # async with session.begin()은 JPA의 @Transactional과 같습니다.
        async with session.begin():
            for data in articles_data:
                # 1. Insert 문 생성
                stmt = insert(Article).values(
                    url=data['url'],
                    title=data['title'],
                    source=data['source'],
                    published_at=data.get('published_at'),  # 날짜 파싱 로직 추가 전까지는 None 혹은 현재시간
                    raw_content=data['raw_content'],
                    summary=data.get('summary'),
                    sentiment=data.get('sentiment')
                )

                # 2. PostgreSQL 전용 Upsert (ON CONFLICT)
                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements=['url'],
                    set_={
                        "summary": stmt.excluded.summary,
                        "sentiment": stmt.excluded.sentiment,
                        "published_at": stmt.excluded.published_at
                    }
                )
                await session.execute(upsert_stmt)
    print(f"[Load] {len(articles_data)}건의 데이터 처리가 완료되었습니다.")