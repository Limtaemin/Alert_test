import os
import time
import random
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
        # 일반 사이트용 브라우저
        browser = p.chromium.launch(headless=True)
        
        # 고연 사이트용 특별 우회 브라우저 (Proxy 추가)
        # 무료 프록시는 수시로 죽기 때문에, 만약 안되면 다른 프록시 서비스를 찾아야 합니다.
        # 일단은 가장 범용적인 우회 설정을 시도합니다.
        proxy_browser = p.chromium.launch(headless=True, proxy={
            "server": "per-context" # 각 사이트별로 다른 설정 적용 가능
        })

        for site in SITES:
            # 고연은 특별 관리, 나머지는 일반 관리
            if site['name'] == '고연':
                # 고연 전용: '스마트 프록시' 혹은 '레퍼러 세탁'을 더 강하게 적용
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    viewport={'width': 1280, 'height': 800},
                    extra_http_headers={
                        "Referer": "https://search.naver.com/search.naver?query=고연"
                    }
                )
            else:
                context = browser.new_context(ignore_https_errors=True)

            page = context.new_page()
            try:
                print(f"[{site['name']}] 접속 시도...")
                page.goto(site['url'], wait_until="domcontentloaded", timeout=60000)
                time.sleep(random.uniform(5, 8)) # 고연은 더 오래 기다려줌
                
                title = ""
                # 공통 추출 로직
                if site['name'] == '부산대_기공':
                    rows = page.query_selector_all('.board-list02 table tbody tr')
                    for row in rows:
                        if 'notice' in row.inner_html() or 'icon_notice' in row.inner_html(): continue
                        link = row.query_selector('td.title.left a')
                        if link:
                            title = link.inner_text().strip()
                            break
                else:
                    # 모든 a 태그 중 wr_id가 포함된 '진짜 제목' 찾기
                    links = page.query_selector_all("a[href*='wr_id=']")
                    for l in links:
                        txt = l.inner_text().strip()
                        if len(txt) > 4 and any(c >= '가' and c <= '힣' for c in txt):
                            title = txt
                            break

                if title:
                    title = title.replace('새글', '').strip()
                    db_file = f"last_{site['name']}_final_victory.txt"
                    
                    if not os.path.exists(db_file):
                        send_telegram(f"🚩 [{site['name']}] 감시 최종 가동\n📌 {title}")
                        with open(db_file, "w", encoding='utf-8') as f: f.write(title)
                    else:
                        with open(db_file, "r", encoding='utf-8') as f: prev = f.read().strip()
                        if title != prev:
                            send_telegram(f"🔔 [{site['name']}] 새 글!\n📌 {title}\n🔗 {site['url']}")
                            with open(db_file, "w", encoding='utf-8') as f: f.write(title)
                else:
                    print(f"[{site['name']}] 실패 (상태: {page.title()})")

            except Exception as e:
                print(f"[{site['name']}] 에러: {str(e)}")
            finally:
                page.close()
                context.close()
        
        browser.close()

if __name__ == "__main__":
    check_updates()
