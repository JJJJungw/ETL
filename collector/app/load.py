from sqlalchemy.dialects.postgresql import insert
from app.database import SessionLocal
from app.models import Article


async def load_to_db(articles_data: list[dict]):

    if not articles_data:
        return

    async with SessionLocal() as session:

        async with session.begin():

            stmt = insert(Article).values(articles_data)

            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=["url"],
                set_={
                    "summary": stmt.excluded.summary,
                    "sentiment": stmt.excluded.sentiment,
                    "category": stmt.excluded.category,
                    "published_at": stmt.excluded.published_at,
                    "image_url": stmt.excluded.image_url,
                    "image_caption": stmt.excluded.image_caption,
                },
            )

            await session.execute(upsert_stmt)

    print(f"[Load] {len(articles_data)}건의 데이터 처리가 완료되었습니다.")