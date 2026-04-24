import os
import time
from playwright.sync_api import sync_playwright
import requests

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

SITES = [
    {
        'name': '고연',
        'url': 'https://www.goyeon.or.kr/bbs/board.php?bo_table=notice',
        'selector': 'td.td_subject div a'
    },
    {
        'name': '스카이웰',
        'url': 'https://www.skywell.or.kr/bbs/board.php?bo_table=idea',
        'selector': 'td.td_subject a'
    },
    {
        'name': '부산대_기공',
        'url': 'https://me.pusan.ac.kr/new/sub05/sub01_05.php',
        'selector': '.board-list02 table tbody tr'
    }
]

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={'chat_id': CHAT_ID, 'text': text}, timeout=10)

def check_updates():
    with sync_playwright() as p:
        # 브라우저 실행 (headless=True는 화면을 띄우지 않음)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36")
        
        for site in SITES:
            page = context.new_page()
            try:
                # 페이지 접속 및 로딩 대기
                page.goto(site['url'], wait_until="networkidle", timeout=60000)
                time.sleep(3) # 추가 로딩 여유 시간
                
                title = ""
                if site['name'] == '부산대_기공':
                    # 부산대: 줄 전체를 가져와서 공지가 아닌 첫 줄 찾기
                    rows = page.query_selector_all(site['selector'])
                    for row in rows:
                        inner_html = row.inner_html()
                        # 'notice' 클래스나 아이콘이 포함되어 있으면 건너뜀
                        if 'notice' in inner_html or 'icon_notice' in inner_html:
                            continue
                        
                        target_link = row.query_selector('td.title.left a')
                        if target_link:
                            title = target_link.inner_text().strip()
                            break
                else:
                    # 고연, 스카이웰: 첫 번째 유효한 링크 찾기
                    elements = page.query_selector_all(site['selector'])
                    for el in elements:
                        txt = el.inner_text().strip()
                        if txt and len(txt) > 2:
                            title = txt
                            break

                if title:
                    title = title.replace('새글', '').strip()
                    db_file = f"last_{site['name']}_ultra.txt" # 새로운 방식이므로 파일명 변경
                    
                    if not os.path.exists(db_file):
                        send_telegram(f"🔥 [{site['name']}] 무적 모드 가동!\n📌 현재글: {title}")
                        with open(db_file, "w", encoding='utf-8') as f:
                            f.write(title)
                    else:
                        with open(db_file, "r", encoding='utf-8') as f:
                            prev_title = f.read().strip()
                        
                        if title != prev_title:
                            send_telegram(f"🔔 [{site['name']}] 새 글!\n📌 {title}\n🔗 {site['url']}")
                            with open(db_file, "w", encoding='utf-8') as f:
                                f.write(title)
                
            except Exception as e:
                print(f"[{site['name']}] 에러: {str(e)}")
            finally:
                page.close()
        
        browser.close()

if __name__ == "__main__":
    check_updates()
