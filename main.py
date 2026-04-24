import requests
from bs4 import BeautifulSoup
import os
import urllib3

# SSL 에러 방지
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    # 더욱 정교해진 브라우저 흉내
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.google.com/'
    }
    
    for site in SITES:
        try:
            res = requests.get(site['url'], headers=headers, timeout=30, verify=False)
            # 한글 깨짐 방지: 사이트가 알려주는 인코딩을 따름
            res.encoding = res.apparent_encoding 
            soup = BeautifulSoup(res.text, 'html.parser')
            
            title = ""
            if site['name'] == '부산대_기공':
                rows = soup.select(site['selector'])
                for row in rows:
                    is_notice = row.select_one('img[src*="icon_notice"]') or '공지' in row.text
                    if not is_notice:
                        link = row.select_one('td.title.left a')
                        if link:
                            title = link.get_text(strip=True)
                            break
            else:
                # 고연, 스카이웰
                target = soup.select_one(site['selector'])
                if target:
                    title = target.get_text(strip=True)

            if title:
                title = title.replace('새글', '').strip()
                # 테스트를 위해 파일명에 _v2를 붙여서 한 번 더 강제로 알림을 오게 해봅시다.
                db_file = f"last_{site['name']}_v2.txt" 
                
                if not os.path.exists(db_file):
                    send_telegram(f"✅ [{site['name']}] 감시 중\n📌 현재글: {title}")
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
                print(f"[{site['name']}] 추출 실패 - 태그 확인 필요")
                
        except Exception as e:
            print(f"[{site['name']}] 에러: {str(e)}")

if __name__ == "__main__":
    check_updates()
