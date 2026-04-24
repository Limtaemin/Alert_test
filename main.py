import requests
from bs4 import BeautifulSoup
import os

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

SITES = [
    {
        'name': '고연',
        'url': 'https://www.goyeon.or.kr/bbs/board.php?bo_table=notice',
        'selector': 'td.td_subject a'
    },
    {
        'name': '스카이웰',
        'url': 'https://www.skywell.or.kr/bbs/board.php?bo_table=idea',
        'selector': 'td.td_subject a'
    },
    {
        'name': '부산대_기공',
        'url': 'https://me.pusan.ac.kr/new/sub05/sub01_05.php',
        'selector': 'td.subject a'
    }
]

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={'chat_id': CHAT_ID, 'text': text}, timeout=10)

def check_updates():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'}
    
    for site in SITES:
        try:
            res = requests.get(site['url'], headers=headers, timeout=20)
            soup = BeautifulSoup(res.content.decode('utf-8', 'ignore'), 'html.parser')
            
            # 태그를 못 찾을 경우를 대비해 여러 시도
            target = soup.select_one(site['selector'])
            
            if target:
                title = target.get_text(strip=True)
                db_file = f"last_{site['name']}.txt"
                
                # 파일이 없으면 만들어서 알림 쏘기
                if not os.path.exists(db_file):
                    send_telegram(f"✅ [{site['name']}] 감시 시작!\n현재 최신글: {title}")
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
                print(f"[{site['name']}] 태그 찾기 실패")
        except Exception as e:
            print(f"[{site['name']}] 에러 발생: {str(e)}")

if __name__ == "__main__":
    check_updates()
