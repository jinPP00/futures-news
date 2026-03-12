# futures_news_crawler.py

import feedparser
import json
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote


# 카테고리별 검색 키워드 (재구성!)
CATEGORIES = {
    '지수': {
        'type': 'search',
        'keywords': [
            '나스닥', 'S&P500', '다우지수', '미국 증시',
            'VIX', '공포지수', '미국 증시 전망'
        ]
    },
    
    '에너지': {
        'type': 'search',
        'keywords': [
            '원유', 'WTI', '브렌트유', '국제유가', '원유 가격',
            '천연가스', '천연가스 가격',
            'OPEC', '원유 재고'
        ]
    },
    
    '금속': {
        'type': 'search',
        'keywords': [
            '금 선물', '금 가격', '국제 금값', '금값', '금 시세',
            '은 선물', '은 가격', '은 시세',
            '구리 가격', '구리 시세',
            '비철금속', '귀금속', '팔라듐', '백금'
        ]
    },
    
    '국제': {
        'type': 'search',
        'keywords': [
            # 트럼프
            '트럼프',
            '트럼프 정책',
            
            # 연준/Fed (핵심!)
            '연준',
            'Fed',
            'FOMC',
            '파월',
            'Fed 금리',
            
            # 미국 경제지표만 (핵심!)
            'NFP',
            '비농업 고용',
            '실업수당',
            '실업률',
            'CPI',
            '소비자물가',
            'PPI',
            '생산자물가',
            'ADP 고용',
            'PMI',
            '제조업 PMI',
            'ISM',
            'GDP',
            '미국 GDP',
            '소매판매',
            '내구재',
            
            # 통화정책
            '금리 결정',
            '금리 인상',
            '금리 인하',
            '양적완화',
            '긴축',
            
            # 미국 경제 (제한적)
            '미국경제 전망',
            '미국 경기침체',
            '미국 인플레이션'
        ],
        'filter_domestic': True
    },
    
    '외환': {
        'type': 'search',
        'keywords': [
            # 달러
            '달러 환율',
            '달러 인덱스',
            'DXY',
            '달러 강세',
            '달러 약세',
            
            # 주요 통화
            '엔화 환율',
            '엔달러',
            '유로 달러',
            '파운드 달러',
            '위안화',
            '원달러 환율',
            
            # 이슈
            '환율 전쟁',
            '통화 전쟁'
        ]
    },
    
    '채권': {
        'type': 'search',
        'keywords': [
            # 미국채
            '미국채',
            '미국채 금리',
            '국채 금리',
            
            # 만기별
            '10년물',
            '2년물',
            '30년물',
            
            # 이슈
            '장단기 금리차',
            '역전',
            '국채 수익률'
        ]
    },
    
    '암호화폐': {
        'type': 'search',
        'keywords': [
            # 주요 코인
            '비트코인',
            '비트코인 가격',
            '이더리움',
            '이더리움 가격',
            
            # 시장
            '암호화폐',
            '가상화폐',
            '비트코인 선물',
            
            # 이슈
            '암호화폐 규제',
            'SEC 암호화폐'
        ]
    }
}

MAX_NEWS_PER_CATEGORY = 10


def is_korean_domestic_news(title):
    """한국 국내 뉴스인지 확인 (제외용)"""
    korean_keywords = [
        # 지역
        '경남', '경북', '부산', '서울', '대구', '울산', '인천', '광주', '대전', '세종',
        '경기', '강원', '충북', '충남', '전북', '전남', '제주',
        '경남일보', '부산일보', '서울신문', '경향신문', '한국경제',
        # 국내 기업
        '삼성전자', 'SK하이닉스', '현대차', 'LG', '포스코', '네이버', '카카오',
        # 국내 이슈
        '코스피', '코스닥', '금융위', '금감원', '국회', '청와대',
        # 부동산
        '아파트', '분양', '청약', '재건축', '재개발',
        # 스포츠
        '첼시', '맨유', '리버풀', '토트넘', '아스널', '맨시티', 'PSG', '바르셀로나', '레알',
        '손흥민', '김민재', '황희찬', '이강인', '이승우',
        '프리미어리그', 'EPL', '챔피언스리그', 'K리그', '라리가', '분데스',
        '야구', '축구', '농구', '배구', '골프', 'KBO', 'NBA', 'MLB',
        '공격수', '수비수', '골키퍼', '감독', '선수',
        # 연예/문화
        '드라마', '영화', '가수', '배우', '아이돌', 'K-POP',
        '방송', 'MBC', 'KBS', 'SBS', 'tvN', '유니폼',
        # 사회
        '사고', '화재', '사망', '체포', '검찰', '경찰', '재판',
        '미안합니다', '사과'
    ]
    
    if any(keyword in title for keyword in korean_keywords):
        return True
    
    return False


def is_international_news(title):
    """국제 뉴스인지 확인 (포함용)"""
    international_keywords = [
        # 국가
        '미국', '중국', '일본', '유럽', '영국', '독일', '프랑스',
        # 기관
        'Fed', '연준', 'ECB', 'BOJ', 'IMF', 'FOMC',
        # 인물
        '트럼프', '바이든', '파월', '옐런',
        # 경제지표
        'CPI', 'PPI', 'NFP', 'ADP', 'PMI', 'GDP', 'ISM',
        # 통화
        '달러', '유로', '엔화',
        # 시장
        '월스트리트', 'S&P', '나스닥', '다우',
        # 키워드
        '글로벌', '세계', '국제', '해외'
    ]
    
    if any(keyword in title for keyword in international_keywords):
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
            print(f"    🔍 필터링된 뉴스: {filtered_count}개")
        
        print(f"    ✅ 수집 완료: {len(news_items)}개")
        return news_items
        
    except Exception as e:
        print(f"    ❌ RSS 파싱 오류: {e}")
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
        
        # 기존 뉴스 가져오기
        existing_category = existing_data.get('categories', {})
        existing_news = existing_category.get(category, [])
        existing_links = {news['link'] for news in existing_news}
        
        print(f"  📚 기존 뉴스: {len(existing_news)}개")
        
        # 필터링 옵션
        filter_domestic = config.get('filter_domestic', False)
        
        # 새 뉴스 수집
        category_news = []
        for keyword in config['keywords']:
            print(f"  🔍 '{keyword}' 검색 중...")
            news_items = fetch_google_news_by_keyword(keyword, filter_domestic)
            category_news.extend(news_items)
        
        print(f"  📦 수집된 전체: {len(category_news)}개")
        
        # 중복 제거 (링크 기준)
        seen_links = set()
        unique_news = []
        for news in category_news:
            if news['link'] not in seen_links:
                seen_links.add(news['link'])
                unique_news.append(news)
        
        print(f"  🔄 중복 제거 후: {len(unique_news)}개")
        
        # 타임스탬프 기준 정렬 (최신순)
        unique_news.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # 기존 뉴스와 합치기
        combined = []
        new_count = 0
        
        # 새 뉴스 추가
        for news in unique_news:
            if news['link'] not in existing_links:
                combined.append(news)
                new_count += 1
        
        # 기존 뉴스 추가
        combined.extend(existing_news)
        
        # 타임스탬프 기준 재정렬
        combined.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # 최대 10개로 제한
        combined = combined[:MAX_NEWS_PER_CATEGORY]
        
        all_news[category] = combined
        total_new += new_count
        
        print(f"  ✅ 최종: 신규 {new_count}개 | 총 {len(combined)}개")
    
    # 3. 전체 뉴스 합치기 (국제가 맨 위)
    total_news = []
    
    # 순서: 국제 → 지수 → 에너지 → 금속 → 외환 → 채권 → 암호화폐
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
