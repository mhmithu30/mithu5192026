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
MIN_POINTS = 40

APUCASH_URL = "https://apucash.com"
SEEN_FILE = "apucash_seen.json"
CHECK_INTERVAL = 30

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=data, timeout=10)
        if r.status_code == 200:
            print("✅ Telegram sent")
            return True
        else:
            print(f"❌ Telegram error: {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ Telegram exception: {e}")
        return False

def scrape_apucash():
    """ApuCash থেকে সঠিক ডাটা সংগ্রহ - HTML স্ট্রাকচার অনুযায়ী"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Checking ApuCash...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
    }
    
    try:
        response = requests.get(APUCASH_URL, headers=headers, timeout=20)
        
        if response.status_code != 200:
            print(f"⚠️ HTTP {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        offers = []
        
        # পদ্ধতি 1: top-offer-wrapper ক্লাস (HTML এ যা দেখছি)
        offer_wrappers = soup.find_all("div", class_="top-offer-wrapper")
        
        for wrapper in offer_wrappers:
            try:
                # ইউজারনেম খোঁজা - h6 ট্যাগে থাকে
                username_elem = wrapper.find("h6")
                username = username_elem.get_text(strip=True) if username_elem else None
                
                # ইউজারনেমের বিকল্প (hd ক্লাসে alt থাকে)
                if not username:
                    hd_elem = wrapper.find("p", class_="hd")
                    if hd_elem:
                        username = hd_elem.get_text(strip=True)
                
                # পয়েন্টস খোঁজা - offer-amount এ থাকে
                amount_elem = wrapper.find("div", class_="offer-amount")
                if amount_elem:
                    points_text = amount_elem.get_text(strip=True)
                    # পয়েন্টস বের করা (যেমন: "1,200💰" বা "41💰")
                    points_match = re.search(r'([\d,]+)', points_text)
                    if points_match:
                        points_str = points_match.group(1).replace(',', '')
                        points_val = float(points_str)
                        
                        if points_val >= MIN_POINTS and username:
                            unique_key = hashlib.md5(f"{username}_{points_val}".encode()).hexdigest()
                            
                            offers.append({
                                "username": username[:30],
                                "points": f"{points_val} coins",
                                "points_val": points_val,
                                "key": unique_key,
                                "time": datetime.now().strftime("%I:%M %p")
                            })
                            print(f"  ✅ {username} - {points_val} coins")
                            
            except Exception as e:
                continue
        
        # পদ্ধতি 2: offer-wrapper ক্লাস (বিকল্প)
        if not offers:
            offer_wrappers = soup.find_all("div", class_="offer-wrapper")
            
            for wrapper in offer_wrappers:
                try:
                    # ইউজারনেম
                    username_elem = wrapper.find("h6")
                    username = username_elem.get_text(strip=True) if username_elem else None
                    
                    if not username:
                        hd_elem = wrapper.find("p", class_="hd")
                        if hd_elem:
                            username = hd_elem.get_text(strip=True)
                    
                    # পয়েন্টস
                    amount_elem = wrapper.find("div", class_="offer-amount")
                    if amount_elem:
                        points_text = amount_elem.get_text(strip=True)
                        points_match = re.search(r'([\d,]+)', points_text)
                        if points_match:
                            points_str = points_match.group(1).replace(',', '')
                            points_val = float(points_str)
                            
                            if points_val >= MIN_POINTS and username:
                                unique_key = hashlib.md5(f"{username}_{points_val}".encode()).hexdigest()
                                offers.append({
                                    "username": username[:30],
                                    "points": f"{points_val} coins",
                                    "points_val": points_val,
                                    "key": unique_key,
                                    "time": datetime.now().strftime("%I:%M %p")
                                })
                                print(f"  ✅ {username} - {points_val} coins")
                except:
                    continue
        
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
    print("🤖 ApuCash Live Offer Notifier (Fixed)")
    print(f"💰 Minimum Points: {MIN_POINTS}+ coins")
    print(f"⏱ Check Interval: {CHECK_INTERVAL} seconds")
    print("="*60)
    
    # স্টার্ট নোটিফিকেশন
    send_telegram(
        f"✅ <b>ApuCash Notifier চালু হয়েছে!</b>\n\n"
        f"🎯 শুধু <b>{MIN_POINTS}+ coins</b> দেখাবে\n"
        f"⏱ চেক ইন্টারভাল: {CHECK_INTERVAL} সেকেন্ড\n\n"
        f"🔍 মনিটরিং চলছে..."
    )
    
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
            offers = scrape_apucash()
            new_count = 0
            
            for offer in offers:
                if offer['key'] not in seen_offers:
                    seen_offers.add(offer['key'])
                    new_count += 1
                    
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
                    
                    # সিন ফাইল সেভ
                    with open(SEEN_FILE, "w") as f:
                        json.dump(list(seen_offers), f)
                    
                    time.sleep(1)
            
            if new_count > 0:
                print(f"✨ {new_count} new offers sent!")
            else:
                print("📭 No new offers")
            
        except Exception as e:
            print(f"❌ Main loop error: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
