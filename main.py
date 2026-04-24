import requests
from bs4 import BeautifulSoup
import os

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

SITES = [
    {
        'name': '고연 공지',
        'url': 'https://www.goyeon.or.kr/bbs/board.php?bo_table=notice',
        'selector': 'td.td_subject a',  # 그누보드 표준 태그
        'encoding': 'utf-8'
    },
    {
        'name': '스카이웰 아이디어',
        'url': 'https://www.skywell.or.kr/bbs/board.php?bo_table=idea',
        'selector': 'td.td_subject a',
        'encoding': 'utf-8'
    },
    {
        'name': '부산대 기공 공지',
        'url': 'https://me.pusan.ac.kr/new/sub05/sub01_05.php',
        'selector': '.board-list td.subject a', # 클래스 경로 보강
        'encoding': 'utf-8'
    }
]

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': text}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"메시지 전송 실패: {e}")

def check_updates():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for site in SITES:
        try:
            res = requests.get(site['url'], headers=headers, timeout=20)
            res.encoding = site['encoding']
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 최신 게시글 찾기
            target = soup.select_one(site['selector'])
            
            if target:
                # 불필요한 공백 및 '새글' 아이콘 텍스트 제거
                title = target.get_text().replace('새글', '').strip()
                
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
                    print(f"[{site['name']}] 업데이트 완료")
                else:
                    print(f"[{site['name']}] 변동 없음")
            else:
                print(f"[{site['name']}] 태그를 찾을 수 없음")
                
        except Exception as e:
            print(f"[{site['name']}] 에러: {e}")

if __name__ == "__main__":
    check_updates()
