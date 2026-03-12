#  ETL Pipeline

뉴스 RSS를 활용하여 실시간 뉴스를 수집하고, AI를 통해 요약 및 감성 분석을 수행하는 자동화 파이프라인입니다.

## 1. System Architecture

프로젝트는 4개의 주요 컨테이너로 구성되며, Docker 네트워크 내에서 유기적으로 통신합니다.


<img width="828" height="341" alt="Image" src="https://github.com/user-attachments/assets/f2a60628-3280-409e-8d77-3dfa779f969e" />


1. **Collector (Python)**: 1시간 주기로 RSS 뉴스 수집 및 AI 서비스에 분석 요청
2. **AI Service (FastAPI)**: 요약,감정분석 모델을 통한 추론
3. **Database (PostgreSQL)**: 분석된 뉴스 데이터의 영속적 저장 (Upsert 적용)
4. **API Service (FastAPI)**: 사용자에게 최종 분석 데이터를 JSON 형태로 제공

---

## 2. 실행 방법 (Quick Start)

### 환경 변수 설정
`.env` 파일을 프로젝트 루트에 생성합니다. (보안을 위해 `.gitignore`에 등록됨)
```bash
# Database
POSTGRES_USER=
POSTGRES_PASSWORD=your_password
POSTGRES_DB=news_etl

# AI Models
SUMMARIZATION_MODEL=digit82/kobart-summarization
SENTIMENT_MODEL=lxyuan/distilbert-base-multilingual-cased-sentiments-student
TRANSFORMERS_CACHE=/models
```
### 서비스 구동
명령어 하나로 전체 파이프라인을 빌드하고 실행합니다.
```bash
docker-compose up -d --build
```
```bash
# AI 서비스 로딩 및 헬스체크 확인
curl http://localhost:8000/health

# 수집된 기사 목록 확인
curl http://localhost:8000/articles
```
