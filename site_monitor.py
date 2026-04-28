"""
GitHub Actions용 사이트 모니터링 봇
"""

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoAlertPresentException
import time
import json
import os
import hashlib
from datetime import datetime
import sys

# ──────────────────────────────────────────
# ⚙️ 설정
# ──────────────────────────────────────────
NO_POST_ALERT_SECONDS = 36
CHECK_INTERVAL_SECONDS = 10
TELEGRAM_RETRY_COUNT = 3
TELEGRAM_RETRY_DELAY = 2

CONFIG_FILE = "sites_config.json"
STATE_FILE = "monitor_state.json"

# 환경변수에서 토큰 읽기 (GitHub Actions)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("❌ 환경변수 설정이 필요합니다!")
    sys.exit(1)

def load_config() -> dict:
    """설정 파일 로드"""
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ {CONFIG_FILE} 파일을 찾을 수 없습니다!")
        return None
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"❌ {CONFIG_FILE} 파일 형식이 잘못되었습니다!")
        return None

CONFIG = load_config()
if not CONFIG:
    sys.exit(1)

SITES = [s for s in CONFIG["sites"] if s.get("enabled", True)]

# ──────────────────────────────────────────
# Selenium 드라이버 설정
# ──────────────────────────────────────────

def create_driver():
    """Chrome 드라이버 생성"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except:
        try:
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e:
            print(f"[Selenium 오류] {e}")
            return None

# ──────────────────────────────────────────
# 텔레그램 메시지 전송
# ──────────────────────────────────────────

def send_telegram(message: str) -> bool:
    """텔레그램으로 메시지 전송"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    
    for attempt in range(TELEGRAM_RETRY_COUNT):
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as e:
            if attempt < TELEGRAM_RETRY_COUNT - 1:
                print(f"[텔레그램 재시도] {attempt + 1}/{TELEGRAM_RETRY_COUNT}")
                time.sleep(TELEGRAM_RETRY_DELAY)
            else:
                print(f"[텔레그램 오류] {e}")
                return False
    
    return False

# ──────────────────────────────────────────
# Alert 처리
# ──────────────────────────────────────────

def handle_alert(driver):
    """페이지의 Alert가 있으면 처리"""
    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        alert.accept()
        print(f"[Alert 처리] {alert_text}")
        time.sleep(1)
    except NoAlertPresentException:
        pass
    except:
        pass

# ──────────────────────────────────────────
# 사이트 크롤링
# ──────────────────────────────────────────

def fetch_posts(site: dict, driver) -> list[dict]:
    """Selenium으로 게시글 목록을 가져옴"""
    try:
        driver.get(site["url"])
        handle_alert(driver)
        
        wait = WebDriverWait(driver, 10)
        
        try:
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, site["css_selector"])))
        except TimeoutException:
            print(f"[타임아웃] {site['name']}")
            return []
        
        elements = driver.find_elements(By.CSS_SELECTOR, site["css_selector"])
        posts = []
        
        for el in elements:
            try:
                link = ""
                if site.get("link_selector"):
                    try:
                        a = el.find_element(By.CSS_SELECTOR, site["link_selector"])
                        href = a.get_attribute("href")
                        if href:
                            if not href.startswith("http"):
                                base_url = "/".join(site["url"].split("/")[:3])
                                link = base_url + href
                            else:
                                link = href
                    except:
                        pass
                
                if site.get("title_selector"):
                    try:
                        title_el = el.find_element(By.CSS_SELECTOR, site["title_selector"])
                        title = title_el.text.strip()
                    except:
                        title = ""
                else:
                    title = ""
                
                if title and len(title) >= 2:
                    posts.append({"title": title, "link": link})
            except:
                continue
        
        return posts[:30]

    except Exception as e:
        print(f"[크롤링 오류] {site['name']}: {e}")
        return []

# ──────────────────────────────────────────
# 상태 관리
# ──────────────────────────────────────────

def load_state() -> dict:
    """이전 상태 불러오기"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_state(state: dict):
    """현재 상태 저장"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def posts_to_hash_set(posts: list[dict]) -> set[str]:
    """게시글 목록을 해시 집합으로 변환"""
    return {hashlib.md5(p["title"].encode()).hexdigest() for p in posts}

# ──────────────────────────────────────────
# 시간 함수
# ──────────────────────────────────────────

def now() -> str:
    """현재 시간 반환"""
    return datetime.now().strftime("%H:%M:%S")

def now_timestamp() -> str:
    """현재 시간을 ISO 형식으로 반환"""
    return datetime.now().isoformat()

# ──────────────────────────────────────────
# 모니터링 로직
# ──────────────────────────────────────────

def check_site(site: dict, state: dict, driver) -> dict:
    """단일 사이트 체크"""
    name = site["name"]
    posts = fetch_posts(site, driver)
    
    if not posts:
        print(f"[{now()}] {name} — 게시글을 가져오지 못했습니다.")
        return state

    current_hashes = posts_to_hash_set(posts)
    
    if name not in state:
        state[name] = {
            "hashes": list(current_hashes),
            "last_new_post_time": now_timestamp(),
            "last_post": posts[0] if posts else None,
            "no_post_alert_sent": False
        }
        print(f"[{now()}] {name} — 초기화 완료 ({len(posts)}개 게시글 저장)")
        return state

    prev_hashes = set(state[name]["hashes"])
    new_hashes = current_hashes - prev_hashes
    
    if new_hashes:
        new_posts = [p for p in posts if hashlib.md5(p["title"].encode()).hexdigest() in new_hashes]
        print(f"[{now()}] {name} — 새 글 {len(new_posts)}개 발견! 🎉")

        msg_lines = [f"🔔 <b>{name}</b> 새 게시글 {len(new_posts)}개\n"]
        for p in new_posts[:5]:
            if p["link"]:
                msg_lines.append(f'• <a href="{p["link"]}">{p["title"]}</a>')
            else:
                msg_lines.append(f'• {p["title"]}')
        
        if len(new_posts) > 5:
            msg_lines.append(f"... 외 {len(new_posts)-5}개")
        
        msg_lines.append(f'\n🔗 <a href="{site["url"]}">게시판 바로가기</a>')

        send_telegram("\n".join(msg_lines))
        
        state[name]["hashes"] = list(current_hashes)
        state[name]["last_new_post_time"] = now_timestamp()
        state[name]["last_post"] = new_posts[0]
        state[name]["no_post_alert_sent"] = False
    else:
        print(f"[{now()}] {name} — 변경 없음")

    return state

# ──────────────────────────────────────────
# 메인
# ──────────────────────────────────────────

def main():
    print("=" * 60)
    print("  🚀 GitHub Actions 모니터링 시작")
    print("=" * 60)
    print(f"모니터링 사이트: {len(SITES)}개\n")

    site_list = "\n".join(f"• {s['name']}" for s in SITES)
    test_msg = (
        f"✅ GitHub Actions 모니터링 실행!\n\n"
        f"📋 모니터링 사이트:\n{site_list}"
    )
    
    send_telegram(test_msg)

    driver = create_driver()
    if not driver:
        print("드라이버 생성 실패!")
        return
    
    state = load_state()

    try:
        for site in SITES:
            state = check_site(site, state, driver)
            save_state(state)
            time.sleep(2)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
