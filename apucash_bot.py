import requests
import time
import json
import hashlib
import os
from datetime import datetime

# ================== কনফিগারেশন ==================
BOT_TOKEN = "8760185059:AAElry-u0BYW6ZLiejygJ1UYHcPGMy_vq9s"
CHAT_ID = "6881373105"
MIN_POINTS = 400

# ApuCash এর রিয়েল-টাইম স্ট্রিম URL (যদি থাকে)
STREAM_URL = "https://apucash.com/stream"

def send_telegram(message):
    import requests
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=data, timeout=10)
        return r.status_code == 200
    except:
        return False

def check_apucash_manually():
    """সরাসরি ওয়েবসাইট ভিজিট করে ডাটা নেওয়ার চেষ্টা"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        import re
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Opening browser...")
        
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=options)
        driver.get("https://apucash.com")
        
        # JavaScript রেন্ডার হওয়ার জন্য অপেক্ষা
        time.sleep(5)
        
        # পেজের HTML নিন
        html = driver.page_source
        
        # সব টেক্সট এলিমেন্ট থেকে ডাটা নিন
        elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'point') or contains(text(), 'earned') or contains(text(), 'coin')]")
        
        offers = []
        for elem in elements[:20]:
            text = elem.text
            if text and len(text) > 10:
                # পয়েন্টস খোঁজা
                points_match = re.search(r'(\d+)\s*(?:points?|coins?)', text, re.I)
                if points_match:
                    points = int(points_match.group(1))
                    if points >= MIN_POINTS:
                        # ইউজারনেম খোঁজা
                        name_match = re.search(r'@?([A-Za-z][A-Za-z0-9_]{3,20})', text)
                        if name_match:
                            username = name_match.group(1)
                            key = hashlib.md5(f"{username}_{points}".encode()).hexdigest()
                            offers.append({
                                "username": username,
                                "points": points,
                                "key": key,
                                "text": text[:100]
                            })
        
        driver.quit()
        return offers
        
    except Exception as e:
        print(f"Error: {e}")
        return []

def main():
    print("="*50)
    print("ApuCash Monitor Starting...")
    send_telegram("✅ ApuCash Monitor Started!\n🎯 Looking for 400+ points activities")
    
    seen = set()
    
    while True:
        offers = check_apucash_manually()
        
        for offer in offers:
            if offer['key'] not in seen:
                seen.add(offer['key'])
                msg = f"🟢 ApuCash Activity!\n\n👤 {offer['username']}\n💰 {offer['points']} points"
                send_telegram(msg)
                print(f"Sent: {offer['username']} - {offer['points']} points")
        
        time.sleep(60)

if __name__ == "__main__":
    main()
