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
        # 브라우저 실행 설정 강화
        browser = p.chromium.launch(headless=True)
        
        # 실제 한국인이 사용하는 윈도우 크롬 환경을 완벽 복사
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            ignore_https_errors=True # 부산대 SSL 에러 해결용
        )

        # 봇 감지 변수 무력화
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        for site in SITES:
            page = context.new_page()
            try:
                print(f"[{site['name']}] 접속 시도...")
                
                # 구글에서 클릭해서 들어온 것처럼 속이기 (Referer 주입)
                page.set_extra_http_headers({
                    "Referer": "https://www.google.com/",
                    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
                })

                # 페이지 이동
                page.goto(site['url'], wait_until="domcontentloaded", timeout=60000)
                
                # 사람처럼 보이게 하기 위해 잠시 대기 후 마우스 살짝 움직임
                time.sleep(random.uniform(3, 6))
                page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                
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
                    # 고연/스카이웰: 더 끈질기게 찾기
                    # 1. 일반적인 제목 태그 시도
                    selectors = ['.td_subject a', 'td.subject a', '.tit a', 'a[href*="wr_id="]']
                    for sel in selectors:
                        elements = page.query_selector_all(sel)
                        for el in elements:
                            txt = el.inner_text().strip()
                            # 5글자 이상, 숫자가 아닌 한글 제목인 경우만 인정
                            if len(txt) > 4 and any(c >= '가' and c <= '힣' for c in txt):
                                title = txt
                                break
                        if title: break

                if title:
                    title = title.replace('새글', '').strip()
                    db_file = f"last_{site['name']}_ultra_final.txt"
                    
                    if not os.path.exists(db_file):
                        send_telegram(f"🛡️ [{site['name']}] 하이퍼 감시 가동\n📌 현재글: {title}")
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
                    p_title = page.title()
                    print(f"[{site['name']}] 내용 추출 실패 (상태: {p_title})")
            
            except Exception as e:
                print(f"[{site['name']}] 에러: {str(e)}")
            finally:
                page.close()
        
        browser.close()

if __name__ == "__main__":
    check_updates()
