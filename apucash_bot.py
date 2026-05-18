import requests
from bs4 import BeautifulSoup
import time
import re
import hashlib
import os
import json
from datetime import datetime
import random

# ================== কনফিগারেশন ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8760185059:AAElry-u0BYW6ZLiejygJ1UYHcPGMy_vq9s")
CHAT_ID = os.environ.get("CHAT_ID", "6881373105")
MIN_POINTS = 400

APUCASH_URL = "https://apucash.com"
SEEN_FILE = "apucash_seen.json"
CHECK_INTERVAL = 60

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=data, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def scrape_apucash():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Checking ApuCash...")
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }
    
    try:
        response = requests.get(APUCASH_URL, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"⚠️ HTTP {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        offers = []
        
        # পদ্ধতি 1: HTML এলিমেন্ট থেকে সরাসরি ইউজারনেম ও পয়েন্টস বের করা
        # ApuCash এ সাধারণত activity ফিড থাকে
        
        # সব activity items খোঁজা
        activity_items = soup.find_all("div", class_=re.compile(r"activity|feed|item", re.I))
        
        if not activity_items:
            # যদি না পায়, সব div চেক করা
            activity_items = soup.find_all("div")
        
        for item in activity_items:
            try:
                item_text = item.get_text()
                
                # পয়েন্টস খোঁজা (বিভিন্ন ফরম্যাট)
                points_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:points?|pts?|coins?)', item_text, re.I)
                if not points_match:
                    points_match = re.search(r'[\$](\d+(?:\.\d+)?)', item_text)
                
                if points_match:
                    points_val = float(points_match.group(1))
                    
                    if points_val >= MIN_POINTS:
                        # ইউজারনেম খোঁজা - সঠিকভাবে
                        username = None
                        
                        # পদ্ধতি A: @username ফরম্যাট
                        at_match = re.search(r'@([A-Za-z0-9_]{3,25})', item_text)
                        if at_match:
                            username = at_match.group(1)
                        
                        # পদ্ধতি B: "username earned" প্যাটার্ন
                        if not username:
                            earned_match = re.search(r'([A-Za-z][A-Za-z0-9_]{2,20})\s+(?:earned|got|received|completed)', item_text, re.I)
                            if earned_match:
                                username = earned_match.group(1)
                        
                        # পদ্ধতি C: "by username" প্যাটার্ন
                        if not username:
                            by_match = re.search(r'(?:by|from)\s+([A-Za-z][A-Za-z0-9_]{2,20})', item_text, re.I)
                            if by_match:
                                username = by_match.group(1)
                        
                        # পদ্ধতি D: HTML এ username class থাকলে
                        if not username:
                            user_elem = item.find(class_=re.compile(r"user|username|name", re.I))
                            if user_elem:
                                username = user_elem.get_text(strip=True)
                        
                        # পদ্ধতি E: link টেক্সট থেকে
                        if not username:
                            link = item.find("a")
                            if link:
                                link_text = link.get_text(strip=True)
                                if len(link_text) > 2 and not link_text.isdigit():
                                    username = link_text
                        
                        # পদ্ধতি F: সাধারণ টেক্সট থেকে প্রথম শব্দ (যেটা নাম হতে পারে)
                        if not username:
                            words = item_text.split()
                            for word in words[:5]:
                                if len(word) > 2 and word.isalpha() and not word.isdigit():
                                    username = word
                                    break
                        
                        # যদি এখনও ইউজারনেম না পাওয়া যায়, স্কিপ করুন
                        if username and len(username) > 2 and not username.isdigit():
                            unique_key = hashlib.md5(f"{username}_{points_val}".encode()).hexdigest()
                            
                            offers.append({
                                "username": username[:30],
                                "points": f"{points_val} points",
                                "points_val": points_val,
                                "key": unique_key,
                                "time": datetime.now().strftime("%H:%M:%S")
                            })
                            print(f"  ✅ {username} - {points_val} points")
                            
            except Exception as e:
                continue
        
        # পদ্ধতি 2: পুরো HTML টেক্সট থেকে উন্নত Regex
        text = response.text
        
        # আরো স্পেসিফিক প্যাটার্ন শুধু valid ইউজারনেমের জন্য
        patterns = [
            # @username earned X points
            r'@([A-Za-z][A-Za-z0-9_]{2,20})\s+(?:earned|got|received)\s+(\d+(?:\.\d+)?)\s+(?:points?|coins?)',
            
            # username (alphabetical) followed by points
            r'([A-Za-z][A-Za-z0-9_]{3,20})\s+(?:earned|got|received|won)\s+(\d+(?:\.\d+)?)',
            
            # Completed by username for X points
            r'(?:completed|finished)\s+(?:by|from)\s+([A-Za-z][A-Za-z0-9_]{3,20})\s+(?:for|got)\s+(\d+(?:\.\d+)?)',
            
            # X points to username
            r'(\d+(?:\.\d+)?)\s+(?:points?|coins?)\s+(?:to|for)\s+([A-Za-z][A-Za-z0-9_]{3,20})',
        ]
        
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
                            # যদি দুইটাই নম্বর না হয়, ধরুন প্রথমটা ইউজারনেম
                            if not match[0].isdigit() and len(match[0]) > 2:
                                username = match[0]
                                points_val = float(match[1]) if match[1].replace('.', '').isdigit() else 0
                            else:
                                continue
                        
                        if points_val >= MIN_POINTS and username and len(username) > 2 and not username.isdigit():
                            unique_key = hashlib.md5(f"{username}_{points_val}".encode()).hexdigest()
                            
                            if not any(o['key'] == unique_key for o in offers):
                                offers.append({
                                    "username": username[:30],
                                    "points": f"{points_val} points",
                                    "points_val": points_val,
                                    "key": unique_key,
                                    "time": datetime.now().strftime("%H:%M:%S")
                                })
                                print(f"  ✅ Regex: {username} - {points_val} points")
                except:
                    continue
        
        # ডুপ্লিকেট রিমুভ
        unique_offers = []
        seen_keys = set()
        for offer in offers:
            if offer['key'] not in seen_keys:
                seen_keys.add(offer['key'])
                unique_offers.append(offer)
        
        print(f"📊 Total valid offers: {len(unique_offers)}")
        return unique_offers
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def main():
    print("="*60)
    print("🤖 ApuCash Live Offer Notifier")
    print(f"💰 Minimum Points: {MIN_POINTS}")
    print("="*60)
    
    send_telegram(f"✅ <b>ApuCash Notifier Started!</b>\n\n🎯 {MIN_POINTS}+ points only\n⏱ Checking every 60 seconds")
    
    seen_offers = set()
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                seen_offers = set(json.load(f))
            print(f"📚 Loaded {len(seen_offers)} seen offers")
        except:
            pass
    
    while True:
        try:
            offers = scrape_apucash()
            
            for offer in offers:
                if offer['key'] not in seen_offers:
                    seen_offers.add(offer['key'])
                    
                    msg = (
                        f"🟢 <b>New ApuCash Activity!</b>\n\n"
                        f"👤 <b>User:</b> {offer['username']}\n"
                        f"💰 <b>Points:</b> {offer['points']}\n"
                        f"⏱ <b>Time:</b> {offer['time']}"
                    )
                    
                    if send_telegram(msg):
                        print(f"📨 Sent: {offer['username']} - {offer['points']}")
                    
                    with open(SEEN_FILE, "w") as f:
                        json.dump(list(seen_offers), f)
                    
                    time.sleep(1)
            
            if len(offers) == 0:
                print("📭 No new offers")
            
        except Exception as e:
            print(f"❌ Loop error: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
