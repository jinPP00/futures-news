# futures_news_crawler.py

from playwright.async_api import async_playwright
import json
from datetime import datetime
import feedparser
import asyncio


def should_crawl_now():
    """크롤링 실행 여부 - 테스트용"""
    return True, "테스트 모드 - 항상 실행"  # 👈 전체를 이렇게


# def should_crawl_now():
#     """
#     크롤링 실행 여부 결정
#     - 밤 9시(21시) ~ 새벽 4시: 항상 실행 (5분마다)
#     - 오전 4시 ~ 밤 9시: 정각 근처에만 실행 (1시간마다)
#     """
#     now = datetime.now()
#     hour = now.hour
#     minute = now.minute
    
#     # 밤 9시 ~ 새벽 4시: 항상 실행
#     if hour >= 21 or hour < 4:
#         return True, f"밤 시간대 ({hour}시) - 5분마다 실행"
    
#     # 오전 4시 ~ 밤 9시: 정각 근처(0~4분)에만 실행
#     if 4 <= hour < 21:
#         if minute < 5:
#             return True, f"낮 시간대 ({hour}시 정각) - 1시간마다 실행"
#         else:
#             return False, f"낮 시간대 ({hour}:{minute:02d}) - 스킵"
    
#     return False, "알 수 없는 시간"

def classify_category(title):
    """카테고리 자동 분류"""
    title_lower = title.lower()
    
    if any(word in title_lower for word in ['금', 'gold', '은', 'silver', '구리', 'copper', '백금', 'platinum']):
        return '금속'
    elif any(word in title_lower for word in ['원유', 'oil', 'crude', '천연가스', 'natural gas', '가솔린', 'gasoline']):
        return '에너지'
    elif any(word in title_lower for word in ['옥수수', 'corn', '대두', 'soybean', '밀', 'wheat', '곡물']):
        return '곡물'
    elif any(word in title_lower for word in ['s&p', 'nasdaq', '나스닥', 'dow', '다우', '니케이', 'nikkei']):
        return '지수'
    elif any(word in title_lower for word in ['달러', 'dollar', '엔', 'yen', '유로', 'euro', '파운드', 'pound']):
        return '통화'
    elif any(word in title_lower for word in ['비트코인', 'bitcoin', '이더리움', 'ethereum', '암호화폐', 'crypto']):
        return '암호화폐'
    else:
        return '기타'

def extract_symbols(title):
    """제목에서 종목 코드 추출"""
    symbols = []
    title_lower = title.lower()
    
    # 금속
    if '금' in title or 'gold' in title_lower:
        symbols.append('GC')
    if '은' in title or 'silver' in title_lower:
        symbols.append('SI')
    if '구리' in title or 'copper' in title_lower:
        symbols.append('HG')
    
    # 에너지
    if '원유' in title or 'crude' in title_lower or 'wti' in title_lower:
        symbols.append('CL')
    if '천연가스' in title or 'natural gas' in title_lower:
        symbols.append('NG')
    
    # 곡물
    if '옥수수' in title or 'corn' in title_lower:
        symbols.append('ZC')
    if '대두' in title or 'soybean' in title_lower:
        symbols.append('ZS')
    if '밀' in title or 'wheat' in title_lower:
        symbols.append('ZW')
    
    # 지수
    if 's&p' in title_lower:
        symbols.append('ES')
    if '나스닥' in title or 'nasdaq' in title_lower:
        symbols.append('NQ')
    if '다우' in title or 'dow' in title_lower:
        symbols.append('YM')
    
    return symbols

async def crawl_kr_investing():
    """kr.investing.com 한글 뉴스 크롤링"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        news_items = []
        
        try:
            await page.goto('https://kr.investing.com/commodities/real-time-futures', 
                           wait_until='domcontentloaded', 
                           timeout=30000)
            await page.wait_for_timeout(3000)
            
            articles = await page.query_selector_all('article.js-article-item')
            
            for article in articles[:15]:
                try:
                    title_elem = await article.query_selector('.textDiv a')
                    if not title_elem:
                        continue
                    
                    title = await title_elem.inner_text()
                    link = await title_elem.get_attribute('href')
                    
                    if link and not link.startswith('http'):
                        link = f"https://kr.investing.com{link}"
                    
                    time_elem = await article.query_selector('.articleDetails span')
                    time_text = await time_elem.inner_text() if time_elem else '방금'
                    
                    if title and title.strip():
                        news_items.append({
                            'title': title.strip(),
                            'time': time_text.strip(),
                            'link': link,
                            'category': classify_category(title),
                            'symbols': extract_symbols(title),
                            'source': 'Investing.com KR',
                            'lang': 'ko'
                        })
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"❌ kr.investing.com 크롤링 오류: {e}")
        
        await browser.close()
        return news_items

async def fetch_cnbc_rss():
    """CNBC 원자재 RSS (영문)"""
    news_items = []
    
    try:
        feed = feedparser.parse('https://www.cnbc.com/id/100727362/device/rss/rss.html')
        
        for entry in feed.entries[:10]:
            title = entry.title
            
            news_items.append({
                'title': title,
                'time': entry.published if hasattr(entry, 'published') else '최근',
                'link': entry.link,
                'category': classify_category(title),
                'symbols': extract_symbols(title),
                'source': 'CNBC',
                'lang': 'en'
            })
            
    except Exception as e:
        print(f"❌ CNBC RSS 오류: {e}")
    
    return news_items

async def crawl_all_sources():
    """모든 소스 통합 크롤링"""
    print("=" * 50)
    print("🚀 해외선물 뉴스 크롤링 시작")
    print("=" * 50)
    
    all_news = []
    
    # kr.investing.com (한글)
    print("\n📰 Investing.com KR 크롤링 중...")
    kr_news = await crawl_kr_investing()
    all_news.extend(kr_news)
    print(f"✅ {len(kr_news)}개 수집")
    
    # CNBC RSS (영문)
    print("\n📰 CNBC RSS 수집 중...")
    cnbc_news = await fetch_cnbc_rss()
    all_news.extend(cnbc_news)
    print(f"✅ {len(cnbc_news)}개 수집")
    
    # 중복 제거
    seen_titles = set()
    unique_news = []
    
    for news in all_news:
        title_key = news['title'][:30].lower().strip()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_news.append(news)
    
    unique_news = unique_news[:25]
    
    result = {
        'updated_at': datetime.now().isoformat(),
        'update_time_kr': datetime.now().strftime('%Y년 %m월 %d일 %H:%M'),
        'news': unique_news,
        'total_count': len(unique_news),
        'sources': {
            'kr_investing': len(kr_news),
            'cnbc': len(cnbc_news),
            'total_before_dedup': len(all_news),
            'duplicates_removed': len(all_news) - len(unique_news)
        }
    }
    
    with open('futures_news.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 50)
    print(f"✅ 크롤링 완료!")
    print(f"📊 총 수집: {len(all_news)}개")
    print(f"📊 중복 제거 후: {len(unique_news)}개")
    print(f"📊 소스별 - KR: {len(kr_news)}개 | CNBC: {len(cnbc_news)}개")
    print("=" * 50)
    
    return result

async def main():
    """메인 실행 함수"""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    should_run, reason = should_crawl_now()
    
    print(f"\n[{current_time}]")
    print(f"⏰ {reason}")
    
    if not should_run:
        print("⏭️  다음 크롤링 시간까지 대기 중...")
        return
    
    print("🎯 크롤링 시작!\n")
    await crawl_all_sources()

if __name__ == '__main__':
    asyncio.run(main())
