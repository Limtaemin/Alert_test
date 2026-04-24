import requests
from bs4 import BeautifulSoup
import os
import urllib3

# 학교 사이트 SSL 에러 방지
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

SITES = [
    {
        'name': '고연',
        'url': 'https://www.goyeon.or.kr/bbs/board.php?bo_table=notice',
        'selector': '.td_subject a, .bo_tit a' # 여러 패턴 시도
    },
    {
        'name': '스카이웰',
        'url': 'https://www.skywell.or.kr/bbs/board.php?bo_table=idea',
        'selector': '.td_subject a, .bo_tit a'
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
    # 최대한 일반 브라우저처럼 보이게 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    
    for site in SITES:
        try:
            # verify=False로 학교 사이트 SSL 에러 해결
            res = requests.get(site['url'], headers=headers, timeout=30, verify=False)
            soup = BeautifulSoup(res.content, 'html.parser')
            
            # 태그 찾기
            target = soup.select_one(site['selector'])
            
            if target:
                title = target.get_text(strip=True)
                # 제목에서 '공지', '새글' 등 불필요한 단어 정리
                title = title.replace('공지', '').replace('새글', '').strip()
                
                db_file = f"last_{site['name']}.txt"
                
                # 처음 감시 시작할 때 파일 생성 및 알림
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
                    print(f"[{site['name']}] 변동 없음")
            else:
                print(f"[{site['name']}] 태그 찾기 실패 - 사이트 구조 확인 필요")
        except Exception as e:
            print(f"[{site['name']}] 에러 발생: {str(e)}")

if __name__ == "__main__":
    check_updates()
