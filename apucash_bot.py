import requests
from bs4 import BeautifulSoup
import time
import re
import hashlib
import os
import json
from datetime import datetime

# ================== কনফিগারেশন ==================
BOT_TOKEN = "8760185059:AAElry-u0BYW6ZLiejygJ1UYHcPGMy_vq9s"
CHAT_ID = "6881373105"
MIN_POINTS = 4  # শুধু ৪+ পয়েন্ট দেখাবে

APUCASH_URL = "https://apucash.com"
SEEN_FILE = "apucash_seen.json"
CHECK_INTERVAL = 30  # 30 সেকেন্ড

def send_telegram(message):
    """টেলিগ্রামে মেসেজ পাঠান"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=data, timeout=10)
        if r.status_code == 200:
            print(f"✅ Telegram sent")
            return True
        else:
            print(f"❌ Telegram error: {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ Telegram exception: {e}")
        return False

def scrape_apucash():
    """ApuCash থেকে ডাটা সংগ্রহ করুন"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Checking ApuCash...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    try:
        response = requests.get(APUCASH_URL, headers=headers, timeout=20)
        
        if response.status_code != 200:
            print(f"⚠️ HTTP {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        offers = []
        
        # মেথড 1: সব টেক্সট থেকে Regex দিয়ে খোঁজা
        text = response.text
        
        # প্যাটার্ন: "username earned X points" বা "username got X coins"
        patterns = [
            # প্যাটার্ন 1: username followed by points
            r'([A-Za-z0-9_@]{3,30})\s+(?:earned|got|received|won)\s+(\d+(?:\.\d+)?)\s+(?:points?|coins?)',
            
            # প্যাটার্ন 2: points followed by username
            r'(\d+(?:\.\d+)?)\s+(?:points?|coins?)\s+(?:by|from)\s+([A-Za-z0-9_@]{3,30})',
            
            # প্যাটার্ন 3: simple username and number
            r'([A-Za-z0-9_]{3,25}).*?(\d{3,})',  # 3 digits or more
        ]
        
        found_items = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.I)
            for match in matches:
                try:
                    if len(match) == 2:
                        # চেক করুন কোনটা ইউজারনেম আর কোনটা পয়েন্টস
                        if match[0].replace('.', '').isdigit():
                            points_val = float(match[0])
                            username = match[1]
                        elif match[1].replace('.', '').isdigit():
                            points_val = float(match[1])
                            username = match[0]
                        else:
                            continue
                        
                        if points_val >= MIN_POINTS and len(username) > 2:
                            unique_key = hashlib.md5(f"{username}_{points_val}".encode()).hexdigest()
                            found_items.append({
                                "username": username,
                                "points": f"{points_val} points",
                                "points_val": points_val,
                                "key": unique_key,
                                "time": datetime.now().strftime("%H:%M:%S")
                            })
                            print(f"  ✅ Found: {username} - {points_val} points")
                except:
                    continue
        
        # মেথড 2: HTML elements থেকে খোঁজা
        # যেকোনো div যাতে points বা coins আছে
        all_divs = soup.find_all("div")
        for div in all_divs:
            div_text = div.get_text()
            
            # পয়েন্টস খোঁজা
            points_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:points?|coins?)', div_text, re.I)
            if points_match:
                points_val = float(points_match.group(1))
                
                if points_val >= MIN_POINTS:
                    # ইউজারনেম খোঁজা (বিভিন্ন প্যাটার্ন)
                    username = None
                    
                    # @username ফরম্যাট
                    at_match = re.search(r'@([A-Za-z0-9_]{3,25})', div_text)
                    if at_match:
                        username = at_match.group(1)
                    else:
                        # সাধারণ ইউজারনেম প্যাটার্ন
                        name_match = re.search(r'([A-Za-z0-9_]{4,25})', div_text)
                        if name_match:
                            username = name_match.group(1)
                    
                    if username and len(username) > 2:
                        unique_key = hashlib.md5(f"{username}_{points_val}".encode()).hexdigest()
                        
                        # ডুপ্লিকেট চেক
                        if not any(item['key'] == unique_key for item in found_items):
                            found_items.append({
                                "username": username[:30],
                                "points": f"{points_val} points",
                                "points_val": points_val,
                                "key": unique_key,
                                "time": datetime.now().strftime("%H:%M:%S")
                            })
                            print(f"  ✅ Found (HTML): {username} - {points_val} points")
        
        # ডুপ্লিকেট রিমুভ (key based)
        unique_offers = []
        seen_keys = set()
        for offer in found_items:
            if offer['key'] not in seen_keys:
                seen_keys.add(offer['key'])
                unique_offers.append(offer)
        
        print(f"📊 Total offers found: {len(unique_offers)}")
        return unique_offers
        
    except Exception as e:
        print(f"❌ Scraping error: {e}")
        return []

def main():
    print("="*60)
    print("🤖 ApuCash Live Offer Notifier")
    print(f"💰 Minimum Points: {MIN_POINTS}")
    print(f"⏱ Check Interval: {CHECK_INTERVAL} seconds")
    print("="*60)
    
    # বুট স্টার্ট নোটিফিকেশন
    start_msg = (
        f"✅ <b>ApuCash Notifier চালু হয়েছে!</b>\n\n"
        f"🎯 শুধু <b>{MIN_POINTS}+ পয়েন্টস</b> দেখাবে\n"
        f"⏱ চেক ইন্টারভাল: {CHECK_INTERVAL} সেকেন্ড\n\n"
        f"🔍 মনিটরিং চলছে..."
    )
    
    if send_telegram(start_msg):
        print("✅ Startup notification sent")
    else:
        print("❌ Failed to send startup notification")
    
    # সিন ফাইল লোড
    seen_offers = set()
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                seen_offers = set(json.load(f))
            print(f"📚 Loaded {len(seen_offers)} seen offers")
        except:
            print("📚 No seen offers file found")
    
    while True:
        try:
            # ApuCash চেক করুন
            new_offers = scrape_apucash()
            
            # নতুন অফার ফিল্টার করুন
            for offer in new_offers:
                if offer['key'] not in seen_offers:
                    seen_offers.add(offer['key'])
                    
                    # টেলিগ্রামে পাঠান
                    msg = (
                        f"🟢 <b>New ApuCash Activity!</b>\n\n"
                        f"👤 <b>User:</b> {offer['username']}\n"
                        f"💰 <b>Points:</b> {offer['points']}\n"
                        f"⏱ <b>Time:</b> {offer['time']}"
                    )
                    
                    if send_telegram(msg):
                        print(f"📨 Sent: {offer['username']} - {offer['points']}")
                    else:
                        print(f"❌ Failed to send: {offer['username']}")
                    
                    # সিন ফাইল সেভ করুন
                    with open(SEEN_FILE, "w") as f:
                        json.dump(list(seen_offers), f)
                    
                    time.sleep(1)  # রেট লিমিট এড়াতে
            
            if len(new_offers) == 0:
                print("📭 No new offers found")
            
        except Exception as e:
            print(f"❌ Main loop error: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
