import requests
from bs4 import BeautifulSoup
import os
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

SITES = [
    {
        'name': '고연',
        'url': 'https://www.goyeon.or.kr/bbs/board.php?bo_table=notice',
        # 태민님이 찾은 경로에서 순서만 뺀 공통 경로
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
        # 태민님이 찾은 경로의 핵심 부분
        'selector': '.board-list02 table tbody tr' 
    }
]

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={'chat_id': CHAT_ID, 'text': text}, timeout=10)

def check_updates():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
    
    for site in SITES:
        try:
            res = requests.get(site['url'], headers=headers, timeout=30, verify=False)
            soup = BeautifulSoup(res.content, 'html.parser')
            
            title = ""
            if site['name'] == '부산대_기공':
                # 부산대는 공지사항이 아닌 첫 번째 일반 게시글을 찾습니다.
                rows = soup.select(site['selector'])
                for row in rows:
                    # '공지' 아이콘이나 텍스트가 없는 행을 찾음
                    is_notice = row.select_one('img[src*="icon_notice.gif"]') or '공지' in row.text
                    if not is_notice:
                        link = row.select_one('td.title.left a')
                        if link:
                            title = link.get_text(strip=True)
                            break
            else:
                # 고연, 스카이웰은 첫 번째 요소를 가져오되 공백 정리
                target = soup.select_one(site['selector'])
                if target:
                    title = target.get_text(strip=True)

            if title:
                title = title.replace('새글', '').strip()
                db_file = f"last_{site['name']}.txt"
                
                if not os.path.exists(db_file):
                    send_telegram(f"✅ [{site['name']}] 감시 시작!\n현재글: {title}")
                    with open(db_file, "w", encoding='utf-8') as f:
                        f.write(title)
                    continue

                with open(db_file, "r", encoding='utf-8') as f:
                    prev_title = f.read().strip()

                if title != prev_title:
                    send_telegram(f"🔔 [{site['name']}] 새 글!\n📌 {title}\n🔗 {site['url']}")
                    with open(db_file, "w", encoding='utf-8') as f:
                        f.write(title)
            else:
                print(f"[{site['name']}] 제목 추출 실패")
                
        except Exception as e:
            print(f"[{site['name']}] 에러: {str(e)}")

if __name__ == "__main__":
    check_updates()
