import httpx
from bs4 import BeautifulSoup
import datetime
import urllib.parse
from dateutil import parser as date_parser

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
    all_news = []
    base_url = "https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    headers = {"User-Agent": "Mozilla/5.0 ..."} # 헤더 동일

    async with httpx.AsyncClient(timeout=15.0, headers=headers, follow_redirects=True) as client:
        for section_name, keyword in G_SECTIONS.items():
            encoded_query = urllib.parse.quote(keyword)
            rss_url = base_url.format(query=encoded_query)
            
            try:
                response = await client.get(rss_url)
                if response.status_code != 200: continue

                # 구글 뉴스는 XML이므로 'xml' 파서 사용 권장
                soup = BeautifulSoup(response.text, "xml")
                items = soup.find_all("item")

                for item in items[:display_per_section]:
                    title = item.title.get_text(strip=True) if item.title else "제목없음"
                    link = item.link.get_text(strip=True) if item.link else ""
                    
                    # [해결 2] Description에서 텍스트만 깨끗하게 추출
                    raw_description = item.description.get_text(strip=True) if item.description else ""
                    clean_description = BeautifulSoup(raw_description, "html.parser").get_text(separator=" ", strip=True)

                    raw_date = item.pubDate.get_text(strip=True) if item.pubDate else None
                    try:
                        if raw_date:
                            # 1. 날짜 파싱
                            dt = date_parser.parse(raw_date)
                            # 2. [핵심] 시간대 정보를 제거하여 'Naive' 객체로 변환
                            published_at = dt.replace(tzinfo=None)
                        else:
                            published_at = datetime.datetime.now()
                    except Exception:
                        published_at = datetime.datetime.now()

                    all_news.append({
                        "title": title,
                        "url": link,
                        "published_at": published_at,
                        "raw_content": clean_description[:1000],
                        "source": f"구글뉴스-{section_name}"
                    })
                print(f"   {section_name} 수집 완료")
            except Exception as e:
                print(f"   {section_name} 에러: {e}")
                
    return all_news