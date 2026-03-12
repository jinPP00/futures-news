# futures_news_crawler.py

import feedparser
import json
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime


# Google News 토픽 URLs
NEWS_TOPICS = {
    '경제': 'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtdHZHZ0pMVWlnQVAB?hl=ko&gl=KR&ceid=KR:ko',
    '세계': 'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtdHZHZ0pMVWlnQVAB?hl=ko&gl=KR&ceid=KR:ko',
    '비즈니스': 'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtdHZHZ0pMVWlnQVAB?hl=ko&gl=KR&ceid=KR:ko'
}

# 카테고리별 분류 키워드
CATEGORY_KEYWORDS = {
    '국제_필수': [  # 무조건 크롤링
        '트럼프', '연준', 'FOMC'
    ],
    '국제': [  # 세계 토픽에서 추가
        '파월', 'Fed', 'NFP', 'CPI', 'PPI', 'ADP', 'PMI', 'GDP', 'ISM',
        '금리 결정', '금리 인상', '금리 인하', '양적완화', '긴축',
        '미국경제', '중국경제', '유럽경제', 'ECB', 'BOJ'
    ],
    '지수': [
        '나스닥', 'Nasdaq', 'NASDAQ', 'nasdaq',
        'S&P', 's&p', 'S&P500', '에스앤피', '에센피'
    ],
    '에너지': [
        '원유', 'WTI', '브렌트', '천연가스', 'OPEC', '국제유가'
    ],
    '금속': [
        '금', '은', '구리',
        '국제금시세', '금시세', '금 시세', '금값', '금 가격',
        '금 선물', '금선물',
        '은 선물', '은선물', '은 가격',
        '구리 가격', '구리 시세'
    ],
    '외환': [
        '달러 환율', '달러 인덱스', 'DXY', '달러',
        '엔화', '엔달러', '유로', '위안화'
    ],
    '채권': [
        '미국채', '국채', '채권',
        '미국채 금리', '국채 금리', '국채금리',
        '10년물', '2년물', '30년물',
        '장단기 금리차', '금리 역전'
    ],
    '암호화폐': [
        '비트코인', '이더리움', '암호화폐'
    ]
}

MAX_NEWS_PER_CATEGORY = 10


def is_korean_domestic_news(title):
    """한국 국내 뉴스 제외"""
    korean_keywords = [
        # 지역
        '경남', '경북', '부산', '서울', '대구', '울산', '인천', '광주', '대전',
        '경기', '강원', '충북', '충남', '전북', '전남', '제주',
        # 국내 기업
        '삼성전자', 'SK하이닉스', '현대차', 'LG', '네이버', '카카오', '포스코',
        # 국내 이슈
        '코스피', '코스닥', '금융위', '국회', '청와대',
        # 부동산
        '아파트', '분양', '청약', '재건축',
        # 스포츠
        '손흥민', '김민재', '황희찬', 'K리그', '프리미어리그',
        '공격수', '수비수', '골키퍼', '3점슛', '득점', '골', '우승',
        # 연예
        '드라마', '영화', 'K-POP', 'MBC', 'KBS', 'SBS',
        # 일반
        '사고', '화재', '경찰', '검찰', '경선', '후보'
    ]
    
    if any(kw in title for kw in korean_keywords):
        return True
    
    return False


def classify_news_category(title):
    """뉴스를 카테고리별로 분류"""
    # 국제 필수 (최우선)
    for keyword in CATEGORY_KEYWORDS['국제_필수']:
        if keyword in title:
            return '국제'
    
    # 나머지 카테고리
    for category in ['지수', '에너지', '금속', '외환', '채권', '암호화폐']:
        keywords = CATEGORY_KEYWORDS[category]
        if any(kw in title for kw in keywords):
            return category
    
    # 국제 (세계 토픽용)
    if any(kw in title for kw in CATEGORY_KEYWORDS['국제']):
        return '국제'
    
    return None


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
    """RSS 시간을 타임스탬프로 변환"""
    try:
        dt = parsedate_to_datetime(rss_time)
        return dt.timestamp()
    except:
        return 0


def fetch_from_topics():
    """토픽에서 해외 뉴스 수집"""
    print("🌐 Google News 토픽에서 수집 중...")
    
    all_news = []
    
    for topic_name, url in NEWS_TOPICS.items():
        print(f"\n📡 [{topic_name}] 토픽 수집 중...")
        
        try:
            feed = feedparser.parse(url)
            print(f"  📊 전체 항목: {len(feed.entries)}개")
            
            collected = 0
            filtered_domestic = 0
            filtered_uncategorized = 0
            
            for entry in feed.entries[:100]:  # 100개 수집
                try:
                    title = entry.title
                    time_original = entry.published if hasattr(entry, 'published') else None
                    
                    if not time_original:
                        continue
                    
                    # 한국 뉴스 제외
                    if is_korean_domestic_news(title):
                        filtered_domestic += 1
                        continue
                    
                    # 카테고리 분류
                    category = classify_news_category(title)
                    
                    if category:
                        all_news.append({
                            'title': title,
                            'link': entry.link,
                            'time': convert_time_to_relative(time_original),
                            'time_original': time_original,
                            'timestamp': get_timestamp_from_rss(time_original),
                            'category': category,
                            'source': 'Google News',
                            'topic': topic_name  # 어느 토픽에서 왔는지 기록
                        })
                        collected += 1
                    else:
                        filtered_uncategorized += 1
                
                except Exception as e:
                    continue
            
            print(f"  ✅ 수집: {collected}개")
            print(f"  🔍 필터링: 한국뉴스 {filtered_domestic}개 | 미분류 {filtered_uncategorized}개")
            
        except Exception as e:
            print(f"  ❌ 토픽 수집 오류: {e}")
    
    return all_news


def crawl_all_categories():
    """모든 카테고리 뉴스 크롤링"""
    print("=" * 50)
    print("🚀 해외선물 뉴스 크롤링 시작 (토픽 기반)")
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
    
    # 2. 토픽에서 뉴스 수집
    new_news = fetch_from_topics()
    
    print(f"\n📦 수집된 전체 뉴스: {len(new_news)}개")
    
    # 3. 카테고리별로 분류
    categorized = {
        '국제': [],
        '지수': [],
        '에너지': [],
        '금속': [],
        '외환': [],
        '채권': [],
        '암호화폐': []
    }
    
    for news in new_news:
        category = news['category']
        if category in categorized:
            categorized[category].append(news)
    
    # 토픽별 통계
    print("\n📊 토픽별 수집 통계:")
    for topic in ['경제', '세계', '비즈니스']:
        topic_news = [n for n in new_news if n.get('topic') == topic]
        print(f"  - {topic}: {len(topic_news)}개")
    
    print("\n📊 카테고리별 수집 통계:")
    for cat, news_list in categorized.items():
        print(f"  - {cat}: {len(news_list)}개")
    
    # 4. 기존 뉴스와 합치기 + 중복 제거
    all_news = {}
    total_new = 0
    
    for category in categorized.keys():
        print(f"\n📰 [{category}] 처리 중...")
        
        # 기존 뉴스
        existing_category = existing_data.get('categories', {})
        existing_news = existing_category.get(category, [])
        existing_links = {news['link'] for news in existing_news}
        
        print(f"  📚 기존: {len(existing_news)}개")
        
        # 새 뉴스
        new_category_news = categorized[category]
        
        # 중복 제거
        seen_links = set()
        unique_new = []
        for news in new_category_news:
            if news['link'] not in seen_links and news['link'] not in existing_links:
                seen_links.add(news['link'])
                # topic 정보 제거 (최종 JSON에 불필요)
                news_clean = {k: v for k, v in news.items() if k != 'topic'}
                unique_new.append(news_clean)
        
        print(f"  🆕 신규: {len(unique_new)}개")
        
        # 합치기
        combined = unique_new + existing_news
        
        # 타임스탬프 기준 정렬
        combined.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # 최대 10개로 제한
        combined = combined[:MAX_NEWS_PER_CATEGORY]
        
        all_news[category] = combined
        total_new += len(unique_new)
        
        print(f"  ✅ 최종: {len(combined)}개")
    
    # 5. 전체 뉴스 합치기
    total_news = []
    category_order = ['국제', '지수', '에너지', '금속', '외환', '채권', '암호화폐']
    
    for category in category_order:
        for news in all_news.get(category, []):
            total_news.append(news)
    
    # 6. JSON 생성
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
            '외환': len(all_news.get('외환', [])),
            '채권': len(all_news.get('채권', [])),
            '암호화폐': len(all_news.get('암호화폐', [])),
            'total': len(total_news),
            'new_articles': total_new
        }
    }
    
    # 7. 저장
    with open('futures_news.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 8. 요약
    print("\n" + "=" * 50)
    print(f"✅ 크롤링 완료!")
    print(f"📊 전체: {len(total_news)}개")
    print(f"📊 신규: {total_new}개")
    print(f"📊 국제: {len(all_news.get('국제', []))}개")
    print(f"📊 지수: {len(all_news.get('지수', []))}개")
    print(f"📊 에너지: {len(all_news.get('에너지', []))}개")
    print(f"📊 금속: {len(all_news.get('금속', []))}개")
    print(f"📊 외환: {len(all_news.get('외환', []))}개")
    print(f"📊 채권: {len(all_news.get('채권', []))}개")
    print(f"📊 암호화폐: {len(all_news.get('암호화폐', []))}개")
    print("=" * 50)


if __name__ == '__main__':
    crawl_all_categories()
