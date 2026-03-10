from fastapi import FastAPI, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime

from app.database import get_db, engine, Base
from app.models import Article  # 아까 만든 모델 파일

app = FastAPI(title="AI News Analysis API")

# 서버 시작 시 테이블이 없다면 생성 (보험용)
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "api_server"}

@app.get("/articles")
async def read_articles(
    sentiment: Optional[str] = Query(None, description="감성 필터 (positive, negative, neutral)"),
    start_date: Optional[datetime] = Query(None, alias="from", description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[datetime] = Query(None, alias="to", description="종료 날짜 (YYYY-MM-DD)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    # 1. 기본 쿼리 생성
    query = select(Article).order_by(Article.published_at.desc())

    # 2. 필터 조건 추가
    if sentiment:
        query = query.where(Article.sentiment == sentiment)
    if start_date:
        query = query.where(Article.published_at >= start_date)
    if end_date:
        query = query.where(Article.published_at <= end_date)

    # 3. 페이징 적용
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    articles = result.scalars().all()
    
    return articles

@app.get("/articles/{article_id}")
async def read_article(article_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article