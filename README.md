#  ETL Pipeline

뉴스 RSS를 활용하여 실시간 뉴스를 수집하고, AI를 통해 요약 및 감성 분석을 수행하는 자동화 파이프라인입니다.

## 1. System Architecture

프로젝트는 4개의 주요 컨테이너로 구성되며, Docker 네트워크 내에서 유기적으로 통신합니다.


<img width="748" height="341" alt="Image" src="https://github.com/user-attachments/assets/1ad87848-66c5-4110-86fb-78ad64c13bc2" />


1. **Collector (Python)**: 1시간 주기로 RSS 뉴스 수집 및 AI 서비스에 분석 요청
2. **AI Service (FastAPI)**: NLP 모델(KoBART, DistilBERT)을 활용한 추론 수행
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
## 🤖 3. AI 모델 선정 및 트러블슈팅 (Review로 옮겨야함 추후에 옮길 예정)

### 요약 모델: `digit82/kobart-summarization`
* **기술적 부채 해결**: 초기 검토 모델(`ainize/kobart-news`)이 최신 라이브러리 규격 미달로 `RecursionError`를 발생시키는 **기술적 부채** 상태임을 확인했습니다.
* **엔지니어링 의사결정**: 구형 모델 수정 대신 표준 규격을 완벽히 준수하는 최신 모델로 교체하여 **시스템 안정성 및 유지보수성**을 확보했습니다.
* **성능**: 한국어 뉴스 특화 모델로, CPU 환경에서도 빠른 응답 속도와 명확한 요약 성능을 보여줍니다.

### 감성 모델: `lxyuan/distilbert-base-multilingual-cased-sentiments-student`
* **요구사항 최적화**: 별도 로직 없이 모델이 직접 **3개 클래스(Positive, Negative, Neutral)**를 출력하여 과제 요건을 100% 충족합니다.
* **효율성**: 다국어 기반으로 뉴스 전반에 대한 범용성이 높으며, `DistilBERT` 아키텍처를 통한 추론 최적화를 달성했습니다.

## 🔍 3. 기술적 설계 문답 (Q&A)

* **AI 서비스 포트를 외부에 노출하지 않은 이유?**
    * 보안 강화를 위해 외부 노출을 차단했습니다. 컨테이너들은 Docker 내부망 내에서 **서비스 이름(`http://ai:8000`)**을 통해 안전하게 통신합니다.
* **UPSERT를 사용하는 이유?**
    * 중복 수집 시 발생하는 PK 충돌 에러를 방지하고, 데이터의 **무결성과 최신성**을 유지하기 위해 사용합니다.
* **model_cache 볼륨의 필요성?**
    * 컨테이너 재시작 시마다 수백 MB의 모델을 재다운로드하는 **네트워크 낭비 및 서비스 지연**을 방지하기 위함입니다.
* **AI 호출 실패 시 NULL로 저장하는 설계 결정?**
    * **시스템의 견고성(Robustness)**을 최우선으로 고려했습니다. AI 서버의 일시적 장애가 전체 데이터 수집 중단으로 이어지지 않도록 설계했습니다.
