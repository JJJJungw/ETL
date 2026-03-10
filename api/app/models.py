from datetime import datetime
from sqlalchemy import String, Text, func
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
    
    # 수집 시각: DB 서버 타임스탬프 기본값 사용
    collected_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"<Article(title={self.title[:15]}..., sentiment={self.sentiment})>"