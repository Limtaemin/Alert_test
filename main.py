import os
import time
import requests
from playwright.sync_api import sync_playwright

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
ANT_KEY = os.environ.get('SCRAPERANT_API_KEY') # 방금 등록한 API 키

SITES = [
    {
        'name': '고연', 
        'url': 'https://www.goyeon.or.kr/bbs/board.php?bo_table=notice',
        'use_ant': True # 403 차단되는 사이트만 True로 설정
    },
    {
        'name': '스카이웰', 
        'url': 'https://www.skywell.or.kr/bbs/board.php?bo_table=idea',
        'use_ant': False 
    },
    {
        'name': '부산대_기공', 
        'url': 'https://me.pusan.ac.kr/new/sub05/sub01_05.php',
        'use_ant': False
    }
]

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={'chat_id': CHAT_ID, 'text': text})

def get_html_via_ant(url):
    # ScraperAnt를 통해 우회 접속하여 HTML만 받아옵니다.
    api_url = f"https://api.scraperant.com/v2/general?url={url}&x-api-key={ANT_KEY}&browser=true"
    response = requests.get(api_url, timeout=30)
    return response.text if response.status_code == 200 else None

def check_updates():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)

        for site in SITES:
            title = ""
            try:
                if site.get('use_ant') and ANT_KEY:
                    # [우회 모드] 차단된 사이트는 API를 통해 HTML을 긁어옴
                    print(f"[{site['name']}] 우회 접속 중...")
                    html = get_html_via_ant(site['url'])
                    if html:
                        page = context.new_page()
                        page.set_content(html)
                    else: raise Exception("우회 API 응답 실패")
                else:
                    # [일반 모드] 직접 접속
                    page = context.new_page()
                    page.goto(site['url'], wait_until="networkidle", timeout=60000)
                
                # 추출 로직 (이미 검증된 로직)
                if 'pusan' in site['url']:
                    target = page.query_selector(".board-list02 table tbody tr:not(.notice) td.title.left a")
                    if target: title = target.inner_text().strip()
                else:
                    links = page.query_selector_all("a[href*='wr_id=']")
                    for el in links:
                        txt = el.inner_text().strip()
                        if len(txt) > 5 and not txt.isdigit():
                            title = txt
                            break

                if title:
                    db_file = f"last_{site['name']}.txt"
                    if not os.path.exists(db_file):
                        send_telegram(f"✅ [{site['name']}] 모니터링 활성화\n📌 {title}")
                        with open(db_file, "w", encoding='utf-8') as f: f.write(title)
                    else:
                        with open(db_file, "r", encoding='utf-8') as f: prev = f.read().strip()
                        if title != prev:
                            send_telegram(f"🔔 [{site['name']}] 새 글!\n📌 {title}\n🔗 {site['url']}")
                            with open(db_file, "w", encoding='utf-8') as f: f.write(title)
                else:
                    print(f"[{site['name']}] 추출 실패")
            
            except Exception as e:
                print(f"[{site['name']}] 에러 발생: {e}")
            finally:
                if 'page' in locals(): page.close()
        
        browser.close()

if __name__ == "__main__":
    check_updates()
