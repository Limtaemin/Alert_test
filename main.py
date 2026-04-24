import requests
from bs4 import BeautifulSoup
import os

# GitHub Secrets에서 설정한 환경변수 가져오기
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 감시할 사이트 설정
SITES = [
    {
        'name': '고연 공지',
        'url': 'https://www.goyeon.or.kr/bbs/board.php?bo_table=notice',
        'selector': '.td_subject a'
    },
    {
        'name': '스카이웰 아이디어',
        'url': 'https://www.skywell.or.kr/bbs/board.php?bo_table=idea',
        'selector': '.td_subject a'
    },
    {
        'name': '부산대 기공 공지',
        'url': 'https://me.pusan.ac.kr/new/sub05/sub01_05.php',
        'selector': 'td.subject a'
    }
]

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"메시지 전송 실패: {e}")

def check_updates():
    for site in SITES:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(site['url'], headers=headers, timeout=20)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            
            latest_post = soup.select_one(site['selector'])
            
            if latest_post:
                title = latest_post.get_text(strip=True)
                db_file = f"last_{site['name'].replace(' ', '_')}.txt"
                prev_title = ""
                
                if os.path.exists(db_file):
                    with open(db_file, "r", encoding='utf-8') as f:
                        prev_title = f.read().strip()

                if title != prev_title:
                    msg = f"🔔 [{site['name']}] 새 글!\n📌 {title}\n🔗 {site['url']}"
                    send_telegram(msg)
                    with open(db_file, "w", encoding='utf-8') as f:
                        f.write(title)
                    print(f"[{site['name']}] 업데이트: {title}")
                else:
                    print(f"[{site['name']}] 변동 없음")
        except Exception as e:
            print(f"[{site['name']}] 에러: {e}")

if __name__ == "__main__":
    check_updates()
