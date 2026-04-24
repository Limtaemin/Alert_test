import os
import time
from playwright.sync_api import sync_playwright
import requests

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

SITES = [
    {'name': '고연', 'url': 'https://www.goyeon.or.kr/bbs/board.php?bo_table=notice'},
    {'name': '스카이웰', 'url': 'https://www.skywell.or.kr/bbs/board.php?bo_table=idea'},
    {'name': '부산대_기공', 'url': 'https://me.pusan.ac.kr/new/sub05/sub01_05.php'}
]

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={'chat_id': CHAT_ID, 'text': text}, timeout=10)
    except:
        pass

def check_updates():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        # 봇 감지 우회 스크립트
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        for site in SITES:
            page = context.new_page()
            try:
                # 1. 페이지 접속 및 '네트워크 조용해질 때까지' 대기
                print(f"[{site['name']}] 접속 시도 중...")
                page.goto(site['url'], wait_until="networkidle", timeout=60000)
                
                # 2. 특정 요소가 나타날 때까지 명시적 대기 (최대 10초)
                # 게시판 테이블이나 특정 클래스가 나타날 때까지 기다립니다.
                try:
                    page.wait_for_selector("table", timeout=10000)
                except:
                    pass
                
                time.sleep(3) # 추가 렌더링 시간
                title = ""
                
                if site['name'] == '부산대_기공':
                    rows = page.query_selector_all('.board-list02 table tbody tr')
                    for row in rows:
                        if 'notice' in row.inner_html() or 'icon_notice' in row.inner_html():
                            continue
                        link = row.query_selector('td.title.left a')
                        if link:
                            title = link.inner_text().strip()
                            break
                else:
                    # 고연 / 스카이웰 공통: 가장 유연한 방식
                    # 'td' 태그 중에서 제목일 확률이 높은 클래스들을 다 뒤집니다.
                    selectors = ['.td_subject a', '.subject a', 'td.title a', 'div.tit a']
                    for sel in selectors:
                        target = page.query_selector(sel)
                        if target:
                            txt = target.inner_text().strip()
                            if len(txt) > 2 and '공지' not in txt:
                                title = txt
                                break
                    
                    # 만약 위 방법으로도 실패하면, wr_id가 포함된 모든 링크 중 첫 번째를 잡습니다.
                    if not title:
                        links = page.query_selector_all("a[href*='wr_id=']")
                        for l in links:
                            txt = l.inner_text().strip()
                            if len(txt) > 4 and not txt.isdigit():
                                title = txt
                                break

                if title:
                    title = title.replace('새글', '').strip()
                    db_file = f"last_{site['name']}_final_v3.txt"
                    
                    if not os.path.exists(db_file):
                        send_telegram(f"🚀 [{site['name']}] 모니터링 시작\n📌 현재글: {title}")
                        with open(db_file, "w", encoding='utf-8') as f:
                            f.write(title)
                    else:
                        with open(db_file, "r", encoding='utf-8') as f:
                            prev_title = f.read().strip()
                        if title != prev_title:
                            send_telegram(f"🔔 [{site['name']}] 새 글!\n📌 {title}\n🔗 {site['url']}")
                            with open(db_file, "w", encoding='utf-8') as f:
                                f.write(title)
                else:
                    # 디버깅용: 실패 시 현재 페이지의 제목이라도 출력
                    page_title = page.title()
                    print(f"[{site['name']}] 추출 실패 (페이지 제목: {page_title})")
            
            except Exception as e:
                print(f"[{site['name']}] 에러: {str(e)}")
            finally:
                page.close()
        
        browser.close()

if __name__ == "__main__":
    check_updates()
