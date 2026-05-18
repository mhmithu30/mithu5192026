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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8617551433:AAFK1waCKiLv72SErBuf4iK0sduSahJONZo")
CHAT_ID = os.environ.get("CHAT_ID", "6881373105")
MIN_POINTS = 400

APUCASH_URL = "https://apucash.com"
SEEN_FILE = "apucash_seen.json"
CHECK_INTERVAL = 60

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=data, timeout=10)
        if r.status_code == 200:
            print(f"✅ Telegram sent")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

def scrape_apucash():
    """ApuCash থেকে সঠিক ডাটা সংগ্রহ"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Checking ApuCash...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
    }
    
    try:
        response = requests.get(APUCASH_URL, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"⚠️ HTTP {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        offers = []
        
        # ডিবাগ: HTML এর অংশ দেখি
        print("  Debug: Looking for activity patterns...")
        
        # পদ্ধতি 1: JSON-LD স্ক্রিপ্ট খোঁজা (সবচেয়ে নির্ভরযোগ্য)
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                import json as json_module
                data = json_module.loads(script.string)
                if isinstance(data, dict):
                    # এখানে ডাটা পার্স করুন
                    pass
            except:
                pass
        
        # পদ্ধতি 2: meta ট্যাগ থেকে
        meta_tags = soup.find_all("meta")
        for meta in meta_tags:
            if meta.get("property") and "activity" in meta.get("property", "").lower():
                print(f"  Meta found: {meta}")
        
        # পদ্ধতি 3: সব div এর inner text বিশ্লেষণ
        all_divs = soup.find_all("div")
        
        for div in all_divs:
            div_html = str(div)
            div_text = div.get_text()
            
            # শুধু মিনিমাম লেন্থের div বিবেচনা করুন
            if len(div_text) < 20 or len(div_text) > 500:
                continue
            
            # পয়েন্টস প্যাটার্ন (একাধিক ফরম্যাট)
            points_patterns = [
                r'(\d+(?:\.\d+)?)\s*(?:points?|pts?|coins?|credits?)',
                r'[\$€£](\d+(?:\.\d+)?)',
                r'reward[:\s]+(\d+)',
                r'earned\s+(\d+)',
            ]
            
            points_val = 0
            points_str = None
            
            for pattern in points_patterns:
                match = re.search(pattern, div_text, re.I)
                if match:
                    points_val = float(match.group(1))
                    points_str = match.group(0)
                    break
            
            if points_val >= MIN_POINTS:
                # ইউজারনেম প্যাটার্ন (একাধিক ফরম্যাট)
                username_patterns = [
                    r'@([A-Za-z0-9_]{3,25})',
                    r'user[:\s]+([A-Za-z0-9_]{3,25})',
                    r'username[:\s]+([A-Za-z0-9_]{3,25})',
                    r'by\s+([A-Za-z][A-Za-z0-9_]{2,20})',
                    r'([A-Za-z][A-Za-z0-9_]{2,20})\s+(?:completed|earned|got)',
                    r'([A-Za-z][A-Za-z0-9_]{3,20})',
                ]
                
                username = None
                for pattern in username_patterns:
                    match = re.search(pattern, div_text, re.I)
                    if match:
                        potential_name = match.group(1)
                        # চেক করুন এটি শুধু নম্বর কিনা
                        if not potential_name.isdigit() and len(potential_name) > 2:
                            username = potential_name
                            break
                
                if username and points_val >= MIN_POINTS:
                    # অফার নেম খোঁজার চেষ্টা
                    offer_name = "Unknown Offer"
                    offer_patterns = [
                        r'(?:completed|finished)\s+([A-Za-z\s]{5,50})',
                        r'offer[:\s]+([A-Za-z\s]{5,50})',
                    ]
                    for pattern in offer_patterns:
                        match = re.search(pattern, div_text, re.I)
                        if match:
                            offer_name = match.group(1).strip()[:40]
                            break
                    
                    unique_key = hashlib.md5(f"{username}_{points_val}_{offer_name}".encode()).hexdigest()
                    
                    offers.append({
                        "username": username,
                        "points": f"{int(points_val)} points",
                        "points_val": points_val,
                        "offer_name": offer_name,
                        "key": unique_key,
                        "time": datetime.now().strftime("%I:%M %p")
                    })
                    print(f"  ✅ {username} - {int(points_val)} points - {offer_name[:20]}")
        
        # পদ্ধতি 4: API endpoint (যদি থাকে)
        api_endpoints = [
            "https://apucash.com/api/activities",
            "https://apucash.com/api/earnings",
            "https://apucash.com/feed.json",
        ]
        
        for api_url in api_endpoints:
            try:
                api_response = requests.get(api_url, headers=headers, timeout=10)
                if api_response.status_code == 200:
                    try:
                        api_data = api_response.json()
                        if isinstance(api_data, list):
                            for item in api_data:
                                username = item.get("user", {}).get("username", item.get("username"))
                                points_val = item.get("points", item.get("reward", 0))
                                if username and points_val >= MIN_POINTS:
                                    unique_key = hashlib.md5(f"{username}_{points_val}".encode()).hexdigest()
                                    offers.append({
                                        "username": username,
                                        "points": f"{points_val} points",
                                        "points_val": points_val,
                                        "offer_name": item.get("offer", "Unknown"),
                                        "key": unique_key,
                                        "time": datetime.now().strftime("%I:%M %p")
                                    })
                                    print(f"  ✅ API: {username} - {points_val} points")
                    except:
                        pass
            except:
                pass
        
        # ডুপ্লিকেট রিমুভ
        unique_offers = []
        seen_keys = set()
        for offer in offers:
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
    print("🤖 ApuCash Live Offer Notifier (Updated)")
    print(f"💰 Minimum Points: {MIN_POINTS}")
    print("="*60)
    
    # স্টার্ট মেসেজ
    send_telegram(f"✅ <b>ApuCash Notifier Restarted!</b>\n\n🎯 {MIN_POINTS}+ points only\n⏱ Checking every {CHECK_INTERVAL} seconds")
    
    # সিন ফাইল লোড
    seen_offers = set()
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                seen_offers = set(json.load(f))
            print(f"📚 Loaded {len(seen_offers)} seen offers")
        except:
            pass
    
    error_count = 0
    
    while True:
        try:
            offers = scrape_apucash()
            
            if offers:
                error_count = 0
                new_count = 0
                
                for offer in offers:
                    if offer['key'] not in seen_offers:
                        seen_offers.add(offer['key'])
                        new_count += 1
                        
                        msg = (
                            f"🟢 <b>New ApuCash Activity! ({MIN_POINTS}+ points)</b>\n\n"
                            f"👤 <b>User:</b> {offer['username']}\n"
                            f"💰 <b>Points:</b> {offer['points']}\n"
                            f"📋 <b>Offer:</b> {offer.get('offer_name', 'Unknown')}\n"
                            f"⏱ <b>Time:</b> {offer['time']}"
                        )
                        
                        if send_telegram(msg):
                            print(f"📨 Sent: {offer['username']} - {offer['points']}")
                        else:
                            print(f"❌ Failed to send: {offer['username']}")
                        
                        # সিন ফাইল সেভ
                        with open(SEEN_FILE, "w") as f:
                            json.dump(list(seen_offers), f)
                        
                        time.sleep(1)
                
                if new_count > 0:
                    print(f"✨ {new_count} new offers sent!")
                else:
                    print("📭 No new offers (all already seen)")
            else:
                error_count += 1
                print(f"📭 No offers found ({error_count})")
                if error_count > 10:
                    print("⚠️ Multiple empty responses - checking connection...")
                    error_count = 0
            
        except Exception as e:
            print(f"❌ Loop error: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
