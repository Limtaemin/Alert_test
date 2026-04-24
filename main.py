import os
import time
from playwright.sync_api import sync_playwright
import requests

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 고연 사이트의 철벽 방어를 뚫기 위한 '슈퍼 헤더'
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.google.com/" # 구글에서 검색해서 들어온 척 속임수
}

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={'chat_id': CHAT_ID, 'text': text}, timeout=10)

def check_updates():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # ignore_https_errors=True로 부산대 SSL 문제를 해결합니다.
        context = browser.new_context(
            user_agent=HEADERS["User-Agent"],
            ignore_https_errors=True 
        )
        
        sites = [
            {'name': '고연', 'url': 'https://www.goyeon.or.kr/bbs/board.php?bo_table=notice'},
            {'name': '스카이웰', 'url': 'https://www.skywell.or.kr/bbs/board.php?bo_table=idea'},
            {'name': '부산대_기공', 'url': 'https://me.pusan.ac.kr/new/sub05/sub01_05.php'}
        ]

        for site in sites:
            page = context.new_page()
            try:
                # 고연 사이트 접속 시 구글 레퍼러 주입
                if 'goyeon' in site['url']:
                    page.set_extra_http_headers({"Referer": "https://www.google.com/"})
                
                page.goto(site['url'], wait_until="networkidle", timeout=60000)
                time.sleep(5) # 넉넉하게 기다림
                
                title = ""
                # 사이트별 제목 추출 로직 (Playwright 버전)
                if 'pusan' in site['url']:
                    target = page.query_selector(".board-list02 table tbody tr:not(.notice) td.title.left a")
                    if target: title = target.inner_text().strip()
                else:
                    # 고연/스카이웰: wr_id가 포함된 링크 중 첫 번째를 가져옴
                    elements = page.query_selector_all("a[href*='wr_id=']")
                    for el in elements:
                        txt = el.inner_text().strip()
                        if len(txt) > 5 and not txt.isdigit():
                            title = txt
                            break

                if title:
                    db_file = f"last_{site['name']}.txt"
                    # 제목 저장 및 알림 로직 (기존과 동일)
                    if not os.path.exists(db_file):
                        send_telegram(f"🚀 [{site['name']}] 감시 시작: {title}")
                        with open(db_file, "w", encoding='utf-8') as f: f.write(title)
                    else:
                        with open(db_file, "r", encoding='utf-8') as f: prev = f.read().strip()
                        if title != prev:
                            send_telegram(f"🔔 [{site['name']}] 새 글: {title}\n{site['url']}")
                            with open(db_file, "w", encoding='utf-8') as f: f.write(title)
                else:
                    print(f"[{site['name']}] 여전히 추출 실패. 상태: {page.title()}")

            except Exception as e:
                print(f"[{site['name']}] 에러: {e}")
            finally:
                page.close()
        browser.close()

if __name__ == "__main__":
    check_updates()
