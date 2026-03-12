# futures_news_crawler.py

import feedparser
import json
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote


# 카테고리별 검색 키워드 (정교화!)
CATEGORIES = {
    '국제': {
        'type': 'search',
        'keywords': [
            # 필수 키워드
            '트럼프 관세',
            '트럼프 정책',
            '연준 금리',
            '연준 FOMC',
            'Fed 금리',
            'FOMC 회의',
            '파월 의장',
            
            # 경제지표
            '미국 NFP',
            '미국 CPI',
            '미국 PPI',
            '미국 ADP',
            '미국 PMI',
            '미국 GDP',
            '미국 ISM',
            '미국 실업률',
            '미국 고용',
            
            # 통화정책
            '미국 금리 인상',
            '미국 금리 인하',
            '미국 기준금리'
        ],
        'filter_domestic': True
    },
    
    '지수': {
        'type': 'search',
        'keywords': [
            '나스닥 지수',
            '나스닥 선물',
            'S&P500 지수',
            'S&P500 선물',
            '다우존스 지수',
            '다우 선물',
            'VIX 지수',
            '미국 증시 전망'
        ]
    },
    
    '에너지': {
        'type': 'search',
        'keywords': [
            'WTI 원유',
            'WTI 선물',
            '브렌트유 가격',
            '국제 원유 가격',
            '원유 선물',
            '천연가스 선물',
            'OPEC 감산',
            'OPEC 회의'
        ]
    },
    
    '금속': {
        'type': 'search',
        'keywords': [
            '금 선물 가격',
            '국제 금 시세',
            '금 선물 시장',
            '은 선물 가격',
            '은 시세',
            '구리 선물',
            '구리 가격'
        ]
    },
    
    '외환': {
        'type': 'search',
        'keywords': [
            '달러 인덱스',
            'DXY 지수',
            '엔달러 환율',
            '유로달러 환율',
            '파운드달러',
            '달러 강세',
            '달러 약세'
        ]
    },
    
    '채권': {
        'type': 'search',
        'keywords': [
            '미국채 10년물',
            '미국채 금리',
            '미국 국채 금리',
            '장단기 금리차',
            '금리 역전 해소',
            '미국채 시장'
        ]
    },
    
    '암호화폐': {
        'type': 'search',
        'keywords': [
            '비트코인 가격',
            '비트코인 선물',
            '이더리움 가격',
            '암호화폐 시장'
        ]
    }
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
        '아파트', '분양', '청약',
        # 스포츠
        '손흥민', '김민재', '황희찬', 'K리그',
        '공격수', '수비수', '3점슛', '득점', '우승',
        # 연예
        '드라마', '영화', 'K-POP', 'MBC', 'KBS', 'SBS',
        # 일반
        '경찰', '검찰', '경선', '후보', '유니폼'
    ]
    
    if any(kw in title for kw in korean_keywords):
        return True
    
    return False


def is_international_news(title):
    """국제 뉴스인지 확인"""
    international_keywords = [
        '미국', '중국', '일본', '유럽', '영국',
        'Fed', '연준', 'FOMC', '트럼프', '파월',
        'CPI', 'NFP', 'PMI', 'GDP',
        '달러', '유로', '엔화'
    ]
    
    crypto_keywords = ['비트코인', '이더리움', '암호화폐', '코인', '토큰']
    
    if any(kw in title for kw in crypto_keywords):
        return False
    
    if any(kw in title for kw in international_keywords):
        return True
    
    return False


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


def fetch_google_news_by_keyword(keyword, filter_domestic=False):
    """Google News에서 키워드로 뉴스 검색"""
    encoded_keyword = quote(keyword)
    url = f'https://news.google.com/rss/search?q={encoded_keyword}+when:3d&hl=ko&gl=KR&ceid=KR:ko'
    
    try:
        feed = feedparser.parse(url)
        
        print(f"    📡 RSS 상태: {feed.get('status', 'N/A')}")
        print(f"    📊 전체 항목: {len(feed.entries)}개")
        
        news_items = []
        filtered_count = 0
        
        for entry in feed.entries[:20]:
            try:
                title = entry.title
                time_original = entry.published if hasattr(entry, 'published') else None
                
                if not time_original:
                    continue
                
                # 국제 카테고리 필터링
                if filter_domestic:
                    if is_korean_domestic_news(title):
                        filtered_count += 1
                        continue
                    
                    if not is_international_news(title):
                        filtered_count += 1
                        continue
                
                news_items.append({
                    'title': title,
                    'link': entry.link,
                    'time': convert_time_to_relative(time_original),
                    'time_original': time_original,
                    'timestamp': get_timestamp_from_rss(time_original),
                    'source': 'Google News'
                })
            except Exception as e:
                continue
        
        if filter_domestic and filtered_count > 0:
            print(f"    🔍 필터링: {filtered_count}개")
        
        print(f"    ✅ 수집: {len(news_items)}개")
        return news_items
        
    except Exception as e:
        print(f"    ❌ RSS 오류: {e}")
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
    
    for category, config in CATEGORIES.items():
        print(f"\n📰 [{category}] 수집 중...")
        
        # 기존 뉴스
        existing_category = existing_data.get('categories', {})
        existing_news = existing_category.get(category, [])
        existing_links = {news['link'] for news in existing_news}
        
        print(f"  📚 기존: {len(existing_news)}개")
        
        # 필터링 옵션
        filter_domestic = config.get('filter_domestic', False)
        
        # 새 뉴스 수집
        category_news = []
        for keyword in config['keywords']:
            print(f"  🔍 '{keyword}' 검색 중...")
            news_items = fetch_google_news_by_keyword(keyword, filter_domestic)
            category_news.extend(news_items)
        
        print(f"  📦 수집 전체: {len(category_news)}개")
        
        # 중복 제거
        seen_links = set()
        unique_news = []
        for news in category_news:
            if news['link'] not in seen_links:
                seen_links.add(news['link'])
                unique_news.append(news)
        
        print(f"  🔄 중복 제거 후: {len(unique_news)}개")
        
        # 타임스탬프 정렬
        unique_news.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # 기존과 합치기
        combined = []
        new_count = 0
        
        for news in unique_news:
            if news['link'] not in existing_links:
                combined.append(news)
                new_count += 1
        
        combined.extend(existing_news)
        combined.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        combined = combined[:MAX_NEWS_PER_CATEGORY]
        
        all_news[category] = combined
        total_new += new_count
        
        print(f"  ✅ 신규 {new_count}개 | 최종 {len(combined)}개")
    
    # 3. 전체 뉴스 합치기
    total_news = []
    category_order = ['국제', '지수', '에너지', '금속', '외환', '채권', '암호화폐']
    
    for category in category_order:
        if category in all_news:
            for news in all_news[category]:
                news['category'] = category
                total_news.append(news)
    
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
            '외환': len(all_news.get('외환', [])),
            '채권': len(all_news.get('채권', [])),
            '암호화폐': len(all_news.get('암호화폐', [])),
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
