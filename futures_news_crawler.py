# futures_news_crawler.py

import feedparser
import json
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime


# 카테고리별 검색 키워드 (금속 키워드 대폭 추가)
CATEGORIES = {
    '지수': ['나스닥', 'S&P500', '다우지수'],
    '에너지': ['원유', 'WTI', '천연가스', '브렌트유'],
    '금속': [
        '금 선물', '금값', '금 가격', '금시세', '금 전망', '골드',
        '은 가격', '은값', '은시세', '은 전망', '실버',
        '구리 가격', 'gold', 'silver', 'copper'
    ],
    '국제': ['세계경제', '국제시장', '글로벌경제', '세계시황'],
    '기타': ['해외선물', '선물 시장', '파생상품', '미국채', '국채', '달러 환율', '엔화', '유로']
}

MAX_NEWS_PER_CATEGORY = 10  # 카테고리당 최대 뉴스 개수


def convert_time_to_relative(rss_time):
    """RSS 시간을 상대 시간으로 변환"""
    try:
        dt_utc = parsedate_to_datetime(rss_time)
        kst_offset = timezone(timedelta(hours=9))
        dt_kst = dt_utc.astimezone(kst_offset)
        now = datetime.now(kst_offset)
        diff = now - dt_kst
        
        if diff.days > 0:
            return f"{diff.days}일 전"
        elif diff.seconds >= 3600:
            return f"{diff.seconds // 3600}시간 전"
        elif diff.seconds >= 60:
            return f"{diff.seconds // 60}분 전"
        else:
            return "방금 전"
    except:
        return rss_time


def get_timestamp_from_rss(rss_time):
    """RSS 시간을 타임스탬프로 변환 (정렬용)"""
    try:
        dt = parsedate_to_datetime(rss_time)
        return dt.timestamp()
    except:
        return 0


def fetch_google_news_by_keyword(keyword):
    """Google News에서 키워드로 뉴스 검색"""
    # 24시간 이내 뉴스만
    url = f'https://news.google.com/rss/search?q={keyword}+when:1d&hl=ko&gl=KR&ceid=KR:ko'
    
    try:
        feed = feedparser.parse(url)
        news_items = []
        
        for entry in feed.entries[:15]:  # 여유있게 15개 가져오기
            try:
                time_original = entry.published if hasattr(entry, 'published') else None
                
                if not time_original:
                    continue
                
                news_items.append({
                    'title': entry.title,
                    'link': entry.link,
                    'time': convert_time_to_relative(time_original),
                    'time_original': time_original,
                    'timestamp': get_timestamp_from_rss(time_original),
                    'source': 'Google News'
                })
            except:
                continue
        
        return news_items
    except Exception as e:
        print(f"❌ {keyword} 검색 오류: {e}")
        return []


def crawl_all_categories():
    """모든 카테고리 뉴스 크롤링"""
    print("=" * 50)
    print("🚀 해외선물 뉴스 크롤링 시작")
    print("=" * 50)
    
    # 1. 기존 데이터 로드
    existing_data = {}
    try:
        with open('futures_news.json', 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            print(f"\n📚 기존 데이터 로드 완료")
    except FileNotFoundError:
        print(f"\n📚 기존 데이터 없음 (첫 실행)")
    except Exception as e:
        print(f"\n⚠️ 기존 데이터 로드 실패: {e}")
    
    # 2. 카테고리별 뉴스 수집
    all_news = {}
    total_new = 0
    
    for category, keywords in CATEGORIES.items():
        print(f"\n📰 [{category}] 수집 중...")
        
        # 기존 뉴스 가져오기
        existing_category = existing_data.get('categories', {})
        existing_news = existing_category.get(category, [])
        existing_links = {news['link'] for news in existing_news}
        
        # 새 뉴스 수집
        category_news = []
        for keyword in keywords:
            print(f"  🔍 '{keyword}' 검색 중...")
            news_items = fetch_google_news_by_keyword(keyword)
            category_news.extend(news_items)
        
        # 중복 제거 (링크 기준)
        seen_links = set()
        unique_news = []
        for news in category_news:
            if news['link'] not in seen_links:
                seen_links.add(news['link'])
                unique_news.append(news)
        
        # 타임스탬프 기준 정렬 (최신순)
        unique_news.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # 기존 뉴스와 합치기 (새 뉴스가 앞에)
        combined = []
        new_count = 0
        
        # 새 뉴스 추가
        for news in unique_news:
            if news['link'] not in existing_links:
                combined.append(news)
                new_count += 1
        
        # 기존 뉴스 추가
        combined.extend(existing_news)
        
        # 타임스탬프 기준 재정렬 (최신순)
        combined.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # 최대 10개로 제한 (최신 10개만)
        combined = combined[:MAX_NEWS_PER_CATEGORY]
        
        all_news[category] = combined
        total_new += new_count
        
        print(f"  ✅ 신규 {new_count}개 | 총 {len(combined)}개")
    
    # 3. 전체 뉴스 합치기
    total_news = []
    for category, news_list in all_news.items():
        for news in news_list:
            news['category'] = category
            total_news.append(news)
    
    # 전체 뉴스도 타임스탬프 기준 정렬
    total_news.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    
    # 4. JSON 생성
    current_time = datetime.now(timezone(timedelta(hours=9)))
    
    result = {
        'updated_at': current_time.isoformat(),
        'update_time_kr': current_time.strftime('%Y년 %m월 %d일 %H:%M'),
        'categories': all_news,
        'all_news': total_news,
        'statistics': {
            '지수': len(all_news.get('지수', [])),
            '에너지': len(all_news.get('에너지', [])),
            '금속': len(all_news.get('금속', [])),
            '국제': len(all_news.get('국제', [])),
            '기타': len(all_news.get('기타', [])),
            'total': len(total_news),
            'new_articles': total_new
        }
    }
    
    # 5. 저장
    with open('futures_news.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 6. 요약
    print("\n" + "=" * 50)
    print(f"✅ 크롤링 완료!")
    print(f"📊 전체: {len(total_news)}개")
    print(f"📊 신규: {total_new}개")
    print(f"📊 지수: {len(all_news.get('지수', []))}개")
    print(f"📊 에너지: {len(all_news.get('에너지', []))}개")
    print(f"📊 금속: {len(all_news.get('금속', []))}개")
    print(f"📊 국제: {len(all_news.get('국제', []))}개")
    print(f"📊 기타: {len(all_news.get('기타', []))}개")
    print("=" * 50)


if __name__ == '__main__':
    crawl_all_categories()
