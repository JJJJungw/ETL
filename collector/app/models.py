from datetime import datetime,date
from sqlalchemy import String, Text, func, Date, Float
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base  # database.py에서 DeclarativeBase를 상속받은 Base를 가져온다고 가정

class Article(Base):
    __tablename__ = "articles"

    # Mapped[int] 만으로 Integer 타입을 추론합니다.
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # URL은 중복 체크(Upsert)의 기준이므로 unique 설정
    url: Mapped[str] = mapped_column(Text, unique=True)
    
    title: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(Text) # Optional 대신 | None 사용
    
    # 기사 발행 시각
    published_at: Mapped[datetime | None] = mapped_column()
    
    # 원문 본문 (최대 1000자 요건)
    raw_content: Mapped[str | None] = mapped_column(Text)
    
    # AI 분석 결과 (실패 시 NULL 허용)
    summary: Mapped[str | None] = mapped_column(Text)
    sentiment: Mapped[str | None] = mapped_column(String(20))
    category: Mapped[str | None] = mapped_column(String(50))
    image_url: Mapped[str | None] = mapped_column(Text)
    image_caption: Mapped[str | None] = mapped_column(Text)
    # 수집 시각: DB 서버 타임스탬프 기본값 사용
    collected_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        # 출력 시 카테고리도 확인 가능하도록 수정
        return f"<Article(title={self.title[:15]}..., category={self.category}, sentiment={self.sentiment})>"
    
class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # 리포트 대상 날짜 (2026-03-11 형식)
    target_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    
    # 총 수집 건수
    total_count: Mapped[int] = mapped_column(default=0)
    
    # 감성별 비율 (0.0 ~ 100.0 %)
    pos_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    neg_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    neu_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    
    # AI 분석 성공률
    success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    
    # 가장 많이 등장한 단어 Top 5 (예: "삼성,반도체,하락,수출,경제")
    top_keywords: Mapped[str | None] = mapped_column(Text)
    
    # 리포트 생성 시각
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"<Report(date={self.target_date}, total={self.total_count}, top5={self.top_keywords[:20]}...)>"