import feedparser
import json
import os
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote

# 설정
MAX_TOTAL_NEWS = 50
JSON_FILE = 'futures_news.json'

# 검색어 그룹 (카테고리 구분 없이 통합 수집용)
SEARCH_GROUPS = [
    ['트럼프 관세', '연준 금리', 'Fed FOMC', '파월 의장', '미국 CPI', '미국 NFP'],
    ['나스닥 선물', 'S&P500 선물', '다우 선물', 'VIX 지수', '미국 증시 전망'],
    ['WTI 원유 선물', '국제 유가', '천연가스 선물', 'OPEC 감산'],
    ['금 선물 가격', '국제 금 시세', '은 선물', '구리 선물'],
    ['달러 인덱스', 'DXY 지수', '엔달러 환율', '달러 강세'],
    ['미국채 10년물 금리', '미국 국채 수익률', '비트코인 선물']
]

def is_korean_domestic_news(title):
    korean_keywords = ['경남', '경북', '부산', '서울', '삼성전자', '아파트', '분양', '손흥민', 'K리그', '드라마']
    return any(kw in title for kw in korean_keywords)

def convert_time_to_relative(rss_time):
    try:
        dt_utc = parsedate_to_datetime(rss_time)
        kst_offset = timezone(timedelta(hours=9))
        dt_kst = dt_utc.astimezone(kst_offset)
        now = datetime.now(kst_offset)
        diff = now - dt_kst
        if diff.days > 0: return f"{diff.days}일 전"
        if diff.seconds >= 3600: return f"{diff.seconds // 3600}시간 전"
        if diff.seconds >= 60: return f"{diff.seconds // 60}분 전"
        return "방금 전"
    except: return rss_time

def main():
    print("🚀 해외선물 통합 뉴스 크롤링 시작...")
    unique_news = {} # 중복 제거용 딕셔너리 {link: item}

    for keywords in SEARCH_GROUPS:
        query = "(" + " OR ".join(keywords) + ")"
        encoded_query = quote(f'{query} when:1d') # 최근 24시간 뉴스만
        url = f'https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko'
        
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if is_korean_domestic_news(entry.title): continue
                
                link = entry.link
                if link not in unique_news:
                    # 제목과 언론사 분리
                    parts = entry.title.rsplit(' - ', 1)
                    title = parts[0] if len(parts) > 1 else entry.title
                    source = parts[1] if len(parts) > 1 else "Google News"
                    
                    unique_news[link] = {
                        'title': title,
                        'link': link,
                        'source': source,
                        'time': convert_time_to_relative(entry.published),
                        'timestamp': parsedate_to_datetime(entry.published).timestamp()
                    }
        except Exception as e:
            print(f"Error fetching group: {e}")

    # 시간순 정렬 및 개수 제한
    final_list = list(unique_news.values())
    final_list.sort(key=lambda x: x['timestamp'], reverse=True)
    final_list = final_list[:MAX_TOTAL_NEWS]

    now_kst = datetime.now(timezone(timedelta(hours=9)))
    result = {
        'updated_at': now_kst.isoformat(),
        'update_time_kr': now_kst.strftime('%Y-%m-%d %H:%M'),
        'all_news': final_list,
        'total_count': len(final_list)
    }

    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"✅ 완료: 총 {len(final_list)}개 뉴스 저장.")

if __name__ == '__main__':
    main()
