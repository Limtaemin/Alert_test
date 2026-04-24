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
    },
    {
        'name': '스카이웰',
        'url': 'https://www.skywell.or.kr/bbs/board.php?bo_table=idea',
    },
    {
        'name': '부산대_기공',
        'url': 'https://me.pusan.ac.kr/new/sub05/sub01_05.php',
    }
]

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={'chat_id': CHAT_ID, 'text': text}, timeout=10)

def check_updates():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 실제 브라우저와 똑같이 보이도록 설정 강화
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale="ko-KR"
        )
        
        # [핵심] 헤드리스 브라우저임을 들키지 않게 하는 스크립트 주입
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        for site in SITES:
            page = context.new_page()
            try:
                # 고연의 경우 더 정교한 로딩 대기 필요
                page.goto(site['url'], wait_until="networkidle", timeout=60000)
                time.sleep(5) 
                
                title = ""
                
                if site['name'] == '부산대_기공':
                    rows = page.query_selector_all('.board-list02 table tbody tr')
                    for row in rows:
                        if 'notice' in row.inner_html() or 'icon_notice' in row.inner_html():
                            continue
                        target_link = row.query_selector('td.title.left a')
                        if target_link:
                            title = target_link.inner_text().strip()
                            break
                else:
                    # 고연/스카이웰: 링크 패턴 분석을 통한 추출
                    # 모든 <a> 태그를 가져와서 wr_id가 포함된 첫 번째 '진짜 제목'을 찾음
                    links = page.query_selector_all('a')
                    for link in links:
                        href = link.get_attribute('href') or ""
                        txt = link.inner_text().strip()
                        
                        # 그누보드 특유의 게시글 링크 패턴
                        if 'wr_id=' in href and len(txt) > 5:
                            # 번호, 날짜, 조회수 등이 아닌 한글 제목인지 확인
                            if any(c >= '가' and c <= '힣' for c in txt):
                                title = txt
                                break

                if title:
                    title = title.replace('새글', '').strip()
                    db_file = f"last_{site['name']}_ultra_v2.txt" # 기록 초기화를 위해 이름 변경
                    
                    if not os.path.exists(db_file):
                        send_telegram(f"✅ [{site['name']}] 감시 시작\n📌 현재글: {title}")
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
                    print(f"[{site['name']}] 추출 실패 - 사이트가 내용을 숨기고 있음")
            
            except Exception as e:
                print(f"[{site['name']}] 에러: {str(e)}")
            finally:
                page.close()
        
        browser.close()

if __name__ == "__main__":
    check_updates()
