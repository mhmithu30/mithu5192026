import requests
from bs4 import BeautifulSoup
import time
import re
import hashlib
import os
import json
from datetime import datetime

# ================== কনফিগারেশন ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHAT_ID = os.environ.get("CHAT_ID", "YOUR_CHAT_ID_HERE")
MIN_POINTS = 400  # শুধু ৪০০+ পয়েন্ট দেখাবে

APUCASH_URL = "https://apucash.com"
SEEN_FILE = "apucash_seen.json"
CHECK_INTERVAL = 60  # 60 সেকেন্ড পর পর চেক করবে

# ================== ফাংশন ==================
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=data, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram Error: {e}")
        return False

def scrape_apucash():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Checking ApuCash...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    
    try:
        res = requests.get(APUCASH_URL, headers=headers, timeout=15)
        if res.status_code != 200:
            return []

        text = res.text
        offers = []
        
        # Regex প্যাটার্ন: ইউজারনেম + পয়েন্টস
        pattern = r'([A-Za-z0-9_]{3,25}).*?(\d+(?:\.\d+)?)\s*(?:points?|coins?)'
        matches = re.findall(pattern, text, re.I)
        
        for username, points in matches:
            points_val = float(points)
            if points_val >= MIN_POINTS:
                unique_key = hashlib.md5(f"{username}_{points_val}".encode()).hexdigest()
                offers.append({
                    "username": username,
                    "points": f"{points_val} points",
                    "points_val": points_val,
                    "key": unique_key,
                    "time": datetime.now().strftime("%H:%M:%S")
                })
                print(f"  Found: {username} - {points_val} points")
        
        # ডুপ্লিকেট রিমুভ
        unique_offers = {offer['key']: offer for offer in offers}.values()
        return list(unique_offers)
        
    except Exception as e:
        print(f"Error: {e}")
        return []

def main():
    print("="*50)
    print("🤖 ApuCash Live Offer Notifier Started")
    print(f"💰 Minimum Points: {MIN_POINTS}")
    print("="*50)
    
    send_telegram(
        f"✅ <b>ApuCash Notifier চালু হয়েছে!</b>\n\n"
        f"🎯 শুধু <b>{MIN_POINTS}+ পয়েন্টস</b> দেখাবে\n"
        f"⏱ চেক ইন্টারভাল: {CHECK_INTERVAL} সেকেন্ড"
    )
    
    seen = load_seen()
    
    while True:
        offers = scrape_apucash()
        
        for offer in offers:
            if offer['key'] not in seen:
                seen.add(offer['key'])
                msg = (
                    f"🟢 <b>ApuCash High Value Activity!</b>\n\n"
                    f"👤 <b>User:</b> {offer['username']}\n"
                    f"💰 <b>Points:</b> {offer['points']}\n"
                    f"⏱ <b>Time:</b> {offer['time']}"
                )
                if send_telegram(msg):
                    print(f"📨 Sent: {offer['username']} - {offer['points']}")
                time.sleep(1)
        
        save_seen(seen)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()