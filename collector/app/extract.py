import httpx
from bs4 import BeautifulSoup
import datetime
import urllib.parse

# 구글 뉴스를 통해 수집할 분야별 키워드 (네이버 섹션과 대응)
G_SECTIONS = {
    "정치": "국회",
    "경제": "금융",
    "사회": "사건사고",
    "생활/문화": "건강",
    "세계": "미국",
    "IT/과학": "인공지능"
}

async def extract_all_sections(display_per_section: int = 5):
    """
    구글 뉴스 RSS를 통해 국내 주요 언론사 뉴스를 수집합니다. (안정성 최강)
    """
    all_news = []
    # 구글 뉴스 RSS는 한국어(hl=ko)와 한국 지역(gl=KR) 설정이 중요합니다.
    base_url = "https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    print(f"📡 [RSS Extract] 구글 통합 뉴스 피드 수집 시작...")

    async with httpx.AsyncClient(timeout=15.0, headers=headers, follow_redirects=True) as client:
        for section_name, keyword in G_SECTIONS.items():
            # 키워드 인코딩 (한글 깨짐 방지)
            encoded_query = urllib.parse.quote(keyword)
            rss_url = base_url.format(query=encoded_query)
            
            try:
                print(f"   📥 {section_name}({keyword}) 데이터 읽는 중...")
                response = await client.get(rss_url)
                
                if response.status_code != 200:
                    print(f"   ⚠️ {section_name} 응답 실패: {response.status_code}")
                    continue

                # 구글 뉴스는 표준 XML 규격을 매우 잘 지킵니다.
                soup = BeautifulSoup(response.text, "xml")
                items = soup.find_all("item")

                if not items:
                    print(f"   ❓ {section_name} 데이터가 없습니다.")
                    continue

                for item in items[:display_per_section]:
                    title = item.title.get_text(strip=True) if item.title else "제목없음"
                    link = item.link.get_text(strip=True) if item.link else ""
                    # 구글 RSS의 description은 HTML 태그가 섞여있을 수 있어 텍스트만 추출
                    description = item.description.get_text(strip=True) if item.description else ""
                    pub_date = item.pubDate.get_text(strip=True) if item.pubDate else str(datetime.datetime.now())

                    all_news.append({
                        "title": title,
                        "url": link,
                        "published_at": pub_date,
                        "raw_content": description[:1000],
                        "source": f"구글뉴스-{section_name}"
                    })
                
                print(f"   ✅ {section_name} 수집 완료 ({len(items[:display_per_section])}건)")

            except Exception as e:
                print(f"   ❌ {section_name} 에러: {e}")
                continue
                
    print(f"✨ [RSS Extract] 총 {len(all_news)}건 수집 완료")
    return all_news