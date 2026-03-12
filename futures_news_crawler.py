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
    elif any(word in title_lower for word in ['s&p', 'nasdaq', '나스닥', 'dow', '다우', '니케이', 'nikkei', '코스피', '코스닥']):
        return '지수'
    elif any(word in title_lower for word in ['달러', 'dollar', '엔', 'yen', '유로', 'euro', '파운드', 'pound', '위안', '환율']):
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
    if '원유' in title or 'crude' in title_lower or 'wti' in title_lower or 'brent' in title_lower:
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
    if 's&p' in title_lower or 's&p 500' in title_lower:
        symbols.append('ES')
    if '나스닥' in title or 'nasdaq' in title_lower:
        symbols.append('NQ')
    if '다우' in title or 'dow' in title_lower:
        symbols.append('YM')
    
    return symbols

async def fetch_google_news_rss():
    """Google News 한글 뉴스 (원자재/선물)"""
    news_items = []
    
    # 검색어별 Google News RSS
    search_queries = {
        '금 선물': 'https://news.google.com/rss/search?q=금+선물+when:7d&hl=ko&gl=KR&ceid=KR:ko',
        '원유 가격': 'https://news.google.com/rss/search?q=원유+가격+when:7d&hl=ko&gl=KR&ceid=KR:ko',
        '달러 환율': 'https://news.google.com/rss/search?q=달러+환율+when:7d&hl=ko&gl=KR&ceid=KR:ko',
        '천연가스': 'https://news.google.com/rss/search?q=천연가스+when:7d&hl=ko&gl=KR&ceid=KR:ko',
        '구리 가격': 'https://news.google.com/rss/search?q=구리+가격+when:7d&hl=ko&gl=KR&ceid=KR:ko',
    }
    
    try:
        for keyword, url in search_queries.items():
            try:
                feed = feedparser.parse(url)
                
                for entry in feed.entries[:3]:  # 각 검색어당 3개씩
                    title = entry.title
                    
                    # 중복 방지: 너무 짧은 제목 제외
                    if len(title.strip()) < 10:
                        continue
                    
                    news_items.append({
                        'title': title,
                        'time': entry.published if hasattr(entry, 'published') else '최근',
                        'link': entry.link,
                        'category': classify_category(title),
                        'symbols': extract_symbols(title),
                        'source': 'Google News',
                        'lang': 'ko'
                    })
                    
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"❌ Google News RSS 오류: {e}")
    
    return news_items

async def crawl_naver_finance():
    """네이버 금융 원자재 뉴스"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        news_items = []
        
        try:
            # 네이버 금융 국제 시장 뉴스
            await page.goto('https://finance.naver.com/news/news_list.naver?mode=LSS3D&section_id=101&section_id2=258&section_id3=402')
            await page.wait_for_timeout(3000)
            
            # 뉴스 제목 목록
            items = await page.query_selector_all('.articleSubject a')
            
            for item in items[:10]:
                try:
                    title = await item.inner_text()
                    link = await item.get_attribute('href')
                    
                    if link and not link.startswith('http'):
                        link = f"https://finance.naver.com{link}"
                    
                    # 원자재 관련 뉴스만 필터링
                    if any(keyword in title for keyword in [
                        '금', '은', '원유', '달러', '환율', '선물', 
                        '구리', '천연가스', '옥수수', '대두', '밀', 'WTI', '브렌트'
                    ]):
                        news_items.append({
                            'title': title.strip(),
                            'time': '최근',
                            'link': link,
                            'category': classify_category(title),
                            'symbols': extract_symbols(title),
                            'source': '네이버 금융',
                            'lang': 'ko'
                        })
                        
                except:
                    continue
                    
        except Exception as e:
            print(f"❌ 네이버 금융 오류: {e}")
        
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
    """모든 소스 통합 크롤링 (누적 방식 + 3일 자동 삭제)"""
    print("=" * 50)
    print("🚀 해외선물 뉴스 크롤링 시작")
    print("=" * 50)
    
    # 1. 기존 뉴스 불러오기
    existing_news = []
    try:
        with open('futures_news.json', 'r', encoding='utf-8') as f:
            old_data = json.load(f)
            existing_news = old_data.get('news', [])
            print(f"\n📚 기존 뉴스: {len(existing_news)}개")
    except FileNotFoundError:
        print("\n📚 기존 뉴스 없음 (첫 실행)")
    except Exception as e:
        print(f"\n⚠️ 기존 파일 읽기 오류: {e}")
    
    # 2. 새 뉴스 크롤링
    new_news = []
    
    # Google News RSS (한글)
    print("\n📰 Google News 수집 중...")
    google_news = await fetch_google_news_rss()
    new_news.extend(google_news)
    print(f"✅ {len(google_news)}개 수집")
    
    # 네이버 금융 (한글)
    print("\n📰 네이버 금융 크롤링 중...")
    naver_news = await crawl_naver_finance()
    new_news.extend(naver_news)
    print(f"✅ {len(naver_news)}개 수집")
    
    # CNBC RSS (영문)
    print("\n📰 CNBC RSS 수집 중...")
    cnbc_news = await fetch_cnbc_rss()
    new_news.extend(cnbc_news)
    print(f"✅ {len(cnbc_news)}개 수집")
    
    # 3. 새 뉴스에 크롤링 시간 추가
    current_time = datetime.now()
    for news in new_news:
        news['crawled_at'] = current_time.isoformat()
    
    # 4. 기존 뉴스 + 새 뉴스 합치기
    all_news = new_news + existing_news
    
    print(f"\n📊 합계: {len(all_news)}개 (신규 {len(new_news)}개 + 기존 {len(existing_news)}개)")
    
    # 5. 3일 지난 뉴스 삭제
    cutoff_time = current_time - timedelta(days=3)
    filtered_news = []
    deleted_count = 0
    
    for news in all_news:
        # crawled_at 필드가 있는지 확인
        if 'crawled_at' not in news:
            # 기존 뉴스 중 crawled_at 없는 것은 현재 시간으로 설정
            news['crawled_at'] = current_time.isoformat()
            filtered_news.append(news)
        else:
            # 크롤링 시간 확인
            try:
                crawled_time = datetime.fromisoformat(news['crawled_at'])
                if crawled_time > cutoff_time:
                    filtered_news.append(news)
                else:
                    deleted_count += 1
            except:
                # 날짜 파싱 실패시 유지
                filtered_news.append(news)
    
    if deleted_count > 0:
        print(f"🗑️  3일 지난 뉴스 {deleted_count}개 삭제")
    
    # 6. 중복 제거 (제목 + 링크 기준)
    seen = set()
    unique_news = []
    duplicates = 0
    
    for news in filtered_news:
        # 제목 50자 + 링크로 고유 키 생성
        title_key = news['title'][:50].lower().strip()
        link_key = news.get('link', '')
        unique_key = (title_key, link_key)
        
        if unique_key not in seen:
            seen.add(unique_key)
            unique_news.append(news)
        else:
            duplicates += 1
    
    if duplicates > 0:
        print(f"🔄 중복 제거: {duplicates}개")
    
    # 7. 최신순 정렬 (crawled_at 기준)
    unique_news.sort(key=lambda x: x.get('crawled_at', ''), reverse=True)
    
    # 8. 최대 200개로 제한 (안전장치)
    if len(unique_news) > 200:
        unique_news = unique_news[:200]
        print(f"⚠️ 200개로 제한 (너무 많음)")
    
    # 9. 통계 계산
    total_count = len(unique_news)
    
    # 언어별 카운트
    korean_count = sum(1 for n in unique_news if n.get('lang') == 'ko')
    english_count = sum(1 for n in unique_news if n.get('lang') == 'en')
    
    # 소스별 카운트 (새 뉴스만)
    new_google = sum(1 for n in new_news if n.get('source') == 'Google News')
    new_naver = sum(1 for n in new_news if n.get('source') == '네이버 금융')
    new_cnbc = sum(1 for n in new_news if n.get('source') == 'CNBC')
    
    # 10. 결과 JSON 생성
    result = {
        'updated_at': current_time.isoformat(),
        'update_time_kr': current_time.strftime('%Y년 %m월 %d일 %H:%M'),
        'news': unique_news,
        'total_count': total_count,
        'statistics': {
            'korean_news': korean_count,
            'english_news': english_count,
            'new_articles': len(new_news),
            'deleted_old_articles': deleted_count,
            'duplicates_removed': duplicates
        },
        'sources': {
            'google_news': new_google,
            'naver': new_naver,
            'cnbc': new_cnbc
        },
        'retention_policy': '3일 보관'
    }
    
    # 11. JSON 파일 저장
    with open('futures_news.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 12. 최종 요약
    print("\n" + "=" * 50)
    print(f"✅ 크롤링 완료!")
    print(f"📊 최종 뉴스: {total_count}개")
    print(f"📊 신규 추가: {len(new_news)}개")
    print(f"📊 3일 삭제: {deleted_count}개")
    print(f"📊 중복 제거: {duplicates}개")
    print(f"📊 한글/영문: {korean_count}개 / {english_count}개")
    print(f"📊 소스별 - Google: {new_google}개 | 네이버: {new_naver}개 | CNBC: {new_cnbc}개")
    print("=" * 50)
    
    return result

async def main():
    """메인 실행 함수"""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 시간대별 실행 여부 체크
    should_run, reason = should_crawl_now()
    
    print(f"\n[{current_time}]")
    print(f"⏰ {reason}")
    
    if not should_run:
        print("⏭️  다음 크롤링 시간까지 대기 중...")
        return
    
    print("🎯 크롤링 시작!\n")
    
    # 실제 크롤링 실행
    await crawl_all_sources()

if __name__ == '__main__':
    asyncio.run(main())
