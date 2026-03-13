import httpx
from bs4 import BeautifulSoup
import datetime
from dateutil import parser as date_parser

RSS_FEEDS = {
    "정치": "https://www.yonhapnewstv.co.kr/category/news/politics/feed/",
    "경제": "https://www.yonhapnewstv.co.kr/category/news/economy/feed/",
    "사회": "https://www.yonhapnewstv.co.kr/category/news/society/feed/",
    "지역": "https://www.yonhapnewstv.co.kr/category/news/local/feed/",
    "생활/문화": "https://www.yonhapnewstv.co.kr/category/news/culture/feed/",
    "세계": "https://www.yonhapnewstv.co.kr/category/news/international/feed/"
}


# -----------------------------------------
# 기사 페이지에서 og:image 추출
# -----------------------------------------
async def extract_article_image(client, url):

    try:
        res = await client.get(url)

        if res.status_code != 200:
            return None

        soup = BeautifulSoup(res.text, "html.parser")

        og = soup.find("meta", property="og:image")

        if og and og.get("content"):
            return og.get("content")

        img = soup.select_one("img.yna_img")

        if img and img.get("src"):
            return img.get("src")

        img = soup.select_one("article img")

        if img and img.get("src"):
            return img.get("src")

    except Exception as e:
        print("이미지 추출 실패:", e)

    return None

# -----------------------------------------
# 전체 뉴스 수집
# -----------------------------------------
async def extract_all_sections(display_per_section: int = 5):

    all_news = []

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    async with httpx.AsyncClient(
        timeout=20.0,
        headers=headers,
        follow_redirects=True
    ) as client:

        for section_name, rss_url in RSS_FEEDS.items():

            try:

                response = await client.get(rss_url)

                if response.status_code != 200:
                    continue

                soup = BeautifulSoup(response.text, "xml")

                items = soup.find_all("item")

                for item in items[:display_per_section]:

                    title = item.title.get_text(strip=True) if item.title else "제목 없음"

                    link = item.link.get_text(strip=True) if item.link else ""

                    # ---------------------------------
                    # 기사 페이지에서 실제 이미지 추출
                    # ---------------------------------
                    image_url = await extract_article_image(client, link)

                    # description 정제
                    raw_description = item.description.get_text(strip=True) if item.description else ""

                    desc_soup = BeautifulSoup(raw_description, "html.parser")

                    clean_content = desc_soup.get_text(
                        separator=" ",
                        strip=True
                    )

                    # 날짜 파싱
                    raw_date = item.pubDate.get_text(strip=True) if item.pubDate else None

                    try:
                        dt = date_parser.parse(raw_date) if raw_date else datetime.datetime.now()
                        published_at = dt.replace(tzinfo=None)

                    except:
                        published_at = datetime.datetime.now()

                    # 이미지 없는 기사 skip (선택)
                    if not image_url:
                        continue

                    all_news.append({
                        "title": title,
                        "url": link,
                        "published_at": published_at,
                        "raw_content": clean_content[:1000],
                        "image_url": image_url,
                        "source": f"연합뉴스-{section_name}"
                    })

                print(f"{section_name} 수집 완료 ({len(items[:display_per_section])}건)")

            except Exception as e:

                print(f"{section_name} 에러:", str(e))

    return all_news