import feedparser
import json
import os
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote

# 1. 설정
MAX_NEWS_PER_CATEGORY = 10
JSON_FILE = 'futures_news.json'

CATEGORIES = {
    '국제': ['트럼프 관세', '연준 금리', 'Fed FOMC', '파월 의장', '미국 CPI', '미국 NFP'],
    '지수': ['나스닥 선물', '나스닥 지수', 'S&P500 선물', '다우 선물', 'VIX 지수'],
    '에너지': ['WTI 원유', 'WTI 선물', '브렌트유 가격', '천연가스 선물', 'OPEC 감산'],
    '금속': ['금 선물 가격', '국제 금 시세', '은 선물', '구리 선물'],
    '외환': ['달러 인덱스', 'DXY 지수', '엔달러 환율', '달러 강세', '유로달러'],
    '채권': ['미국채 10년물', '미국 국채 금리', '장단기 금리차', '국채 수익률'],
    '암호화폐': ['비트코인 선물', '비트코인 가격', '이더리움 시세', '암호화폐 시장']
}

def is_korean_domestic_news(title):
    """국내 뉴스 필터링"""
    korean_keywords = [
        '경남', '경북', '부산', '서울', '코스피', '코스닥', '삼성전자', 
        '아파트', '분양', '손흥민', 'K리그', '드라마', '영화', '검찰', '경찰'
    ]
    return any(kw in title for kw in korean_keywords)

def convert_time_to_relative(rss_time):
    """RSS 시간을 상대 시간으로 변환 (KST 기준)"""
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

def fetch_google_news(category_name, keywords):
    """카테고리별 뉴스 수집 (OR 연산자로 효율화)"""
    query = "(" + " OR ".join(keywords) + ")"
    encoded_query = quote(f'{query} when:2d') # 최근 2일 이내 뉴스만
    url = f'https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko'
    
    news_items = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.title
            
            # 국내 뉴스 필터링 (국제/지수 등 주요 카테고리만 적용하거나 전체 적용)
            if is_korean_domestic_news(title):
                continue
            
            # 언론사명 분리 (제목 - 언론사)
            parts = title.rsplit(' - ', 1)
            clean_title = parts[0] if len(parts) > 1 else title
            source = parts[1] if len(parts) > 1 else "Google News"

            news_items.append({
                'title': clean_title,
                'link': entry.link,
                'source': source,
                'time': convert_time_to_relative(entry.published),
                'timestamp': parsedate_to_datetime(entry.published).timestamp(),
                'category': category_name
            })
            if len(news_items) >= MAX_NEWS_PER_CATEGORY: break
    except Exception as e:
        print(f"Error fetching {category_name}: {e}")
    return news_items

def main():
    print(f"🚀 크롤링 시작: {datetime.now()}")
    
    # 기존 데이터 로드 (신규 뉴스 판별용)
    existing_data = {}
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            existing_data = json.load(f).get('categories', {})

    all_news_by_category = {}
    total_list = []
    
    for category, keywords in CATEGORIES.items():
        print(f"📦 {category} 수집 중...")
        current_news = fetch_google_news(category, keywords)
        
        # 중복 제거 및 최신화 로직
        existing_links = {item['link'] for item in existing_data.get(category, [])}
        new_items = [n for n in current_news if n['link'] not in existing_links]
        
        # 병합 후 정렬
        combined = (new_items + existing_data.get(category, []))[:MAX_NEWS_PER_CATEGORY]
        combined.sort(key=lambda x: x['timestamp'], reverse=True)
        
        all_news_by_category[category] = combined
        total_list.extend(combined)

    # 전체 리스트 시간순 정렬
    total_list.sort(key=lambda x: x['timestamp'], reverse=True)

    # 결과물 생성
    now_kst = datetime.now(timezone(timedelta(hours=9)))
    result = {
        'updated_at': now_kst.isoformat(),
        'update_time_kr': now_kst.strftime('%Y-%m-%d %H:%M'),
        'categories': all_news_by_category,
        'all_news': total_list,
        'statistics': {cat: len(lst) for cat, lst in all_news_by_category.items()}
    }
    result['statistics']['total'] = len(total_list)

    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 완료: {len(total_list)}개 뉴스 저장됨.")

if __name__ == '__main__':
    main()
