import httpx
from bs4 import BeautifulSoup
import datetime
import urllib.parse
from dateutil import parser as date_parser

# 과제 섹션에 맞춘 연합뉴스TV RSS 리스트
RSS_FEEDS = {
    "정치": "https://www.yonhapnewstv.co.kr/category/news/politics/feed/",
    "경제": "https://www.yonhapnewstv.co.kr/category/news/economy/feed/",
    "사회": "https://www.yonhapnewstv.co.kr/category/news/society/feed/",
    "IT/과학": "https://www.yonhapnewstv.co.kr/category/news/it/feed/",
    "생활/문화": "https://www.yonhapnewstv.co.kr/category/news/culture/feed/",
    "세계": "https://www.yonhapnewstv.co.kr/category/news/international/feed/"
}

async def extract_all_sections(display_per_section: int = 5):
    all_news = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async with httpx.AsyncClient(timeout=20.0, headers=headers, follow_redirects=True) as client:
        for section_name, rss_url in RSS_FEEDS.items():
            try:
                response = await client.get(rss_url)
                if response.status_code != 200:
                    print(f"    {section_name} 응답 실패: {response.status_code}")
                    continue

                # RSS는 XML 형식이므로 'xml' 파서 사용
                soup = BeautifulSoup(response.text, "xml")
                items = soup.find_all("item")

                for item in items[:display_per_section]:
                    title = item.title.get_text(strip=True) if item.title else "제목 없음"
                    link = item.link.get_text(strip=True) if item.link else ""
                    
                    # [핵심] Description에서 기사 본문 앞부분(최대 1000자) 추출
                    raw_description = item.description.get_text(strip=True) if item.description else ""
                    # HTML 태그 제거 및 텍스트 정제
                    clean_content = BeautifulSoup(raw_description, "html.parser").get_text(separator=" ", strip=True)

                    # 날짜 파싱 (Naive 객체로 변환)
                    raw_date = item.pubDate.get_text(strip=True) if item.pubDate else None
                    try:
                        if raw_date:
                            dt = date_parser.parse(raw_date)
                            published_at = dt.replace(tzinfo=None)
                        else:
                            published_at = datetime.datetime.now()
                    except:
                        published_at = datetime.datetime.now()

                    all_news.append({
                        "title": title,
                        "url": link,
                        "published_at": published_at,
                        "raw_content": clean_content[:1000], # 과제 스펙 준수
                        "source": f"연합뉴스-{section_name}"
                    })
                print(f"   {section_name} 수집 완료 ({len(items[:display_per_section])}건)")
                
            except Exception as e:
                print(f"   {section_name} 에러: {str(e)}")
                
    return all_news