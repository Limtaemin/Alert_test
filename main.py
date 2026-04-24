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
        # 실제 사용 중인 크롬과 거의 동일한 환경 설정
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        
        for site in SITES:
            page = context.new_page()
            try:
                # 1. 페이지 접속 (충분한 시간 대기)
                page.goto(site['url'], wait_until="domcontentloaded", timeout=60000)
                time.sleep(5) # 스크립트 실행 대기 시간 대폭 늘림
                
                title = ""
                
                if site['name'] == '부산대_기공':
                    # 부산대는 이미 잘 작동하므로 기존 로직 유지
                    rows = page.query_selector_all('.board-list02 table tbody tr')
                    for row in rows:
                        if 'notice' in row.inner_html() or 'icon_notice' in row.inner_html():
                            continue
                        target_link = row.query_selector('td.title.left a')
                        if target_link:
                            title = target_link.inner_text().strip()
                            break
                else:
                    # 고연/스카이웰: 더 넓은 범위에서 제목 후보군을 찾음
                    # 게시판 링크 특성(wr_id 포함)을 가진 태그를 직접 찾습니다.
                    links = page.query_selector_all('a')
                    for link in links:
                        href = link.get_attribute('href') or ""
                        txt = link.inner_text().strip()
                        
                        # 그누보드 게시판 링크의 공통점: wr_id가 포함됨
                        if 'wr_id=' in href and len(txt) > 5:
                            # '공지'나 '번호'가 아닌 진짜 제목일 가능성이 높은 첫 번째 링크 선택
                            if not txt.isdigit() and '공지' not in txt:
                                title = txt
                                break

                if title:
                    title = title.replace('새글', '').strip()
                    db_file = f"last_{site['name']}_final.txt"
                    
                    if not os.path.exists(db_file):
                        send_telegram(f"🛡️ [{site['name']}] 감시 활성화\n📌 현재글: {title}")
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
                    print(f"[{site['name']}] 제목 추출 실패 (사이트 구조 확인 필요)")
            
            except Exception as e:
                print(f"[{site['name']}] 에러: {str(e)}")
            finally:
                page.close()
        
        browser.close()

if __name__ == "__main__":
    check_updates()
