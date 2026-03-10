import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# 반드시 .env와 docker-compose.yml에 정의된 이름을 사용하세요.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    # 이 로그가 찍힌다면 도커 환경변수 주입 설정이 잘못된 겁니다.
    raise ValueError("DATABASE_URL 환경변수가 설정되지 않았습니다.")

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False # 운영 시에는 False, SQL 로그 보고 싶으면 True
)

SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()