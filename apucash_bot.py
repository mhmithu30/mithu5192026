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
MIN_POINTS = 40  # 40+ পয়েন্টস

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
    """ApuCash থেকে সঠিক ডাটা সংগ্রহ - সঠিক ইউজারনেম সহ"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Checking ApuCash...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    try:
        response = requests.get(APUCASH_URL, headers=headers, timeout=20)
        
        if response.status_code != 200:
            print(f"⚠️ HTTP {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        offers = []
        
        # top-offer-wrapper ক্লাস থেকে ডাটা নেওয়া
        offer_wrappers = soup.find_all("div", class_="top-offer-wrapper")
        
        for wrapper in offer_wrappers:
            try:
                # ========== সঠিক ইউজারনেম (hd ক্লাস থেকে) ==========
                username = None
                hd_elem = wrapper.find("p", class_="hd")
                if hd_elem:
                    username = hd_elem.get_text(strip=True)
                
                # যদি hd না পাওয়া যায়, তাহলে alt এট্রিবিউট থেকে নেওয়া
                if not username:
                    img_elem = wrapper.find("img")
                    if img_elem and img_elem.get('alt'):
                        username = img_elem.get('alt')
                
                # Offerwall নাম (এটি শুধু তথ্যের জন্য রাখা হয়েছে)
                offerwall = None
                offerwall_elem = wrapper.find("h6")
                if offerwall_elem:
                    offerwall = offerwall_elem.get_text(strip=True)
                
                # পয়েন্টস
                amount_elem = wrapper.find("div", class_="offer-amount")
                points_val = 0
                
                if amount_elem:
                    points_text = amount_elem.get_text(strip=True)
                    # পয়েন্টস বের করা (যেমন: "1,250🎁" বা "5,000🎁")
                    points_match = re.search(r'([\d,]+)', points_text)
                    if points_match:
                        points_str = points_match.group(1).replace(',', '')
                        points_val = float(points_str)
                
                # চেক করা
                if points_val >= MIN_POINTS and username:
                    unique_key = hashlib.md5(f"{username}_{points_val}".encode()).hexdigest()
                    
                    offers.append({
                        "username": username[:30],           # আসল ইউজারনেম (xyl20yuh)
                        "offerwall": offerwall[:30] if offerwall else "Unknown",  # Offerwall নাম (Adsprem)
                        "points": f"{int(points_val)} coins",
                        "points_val": points_val,
                        "key": unique_key,
                        "time": datetime.now().strftime("%I:%M %p")
                    })
                    print(f"  ✅ {username} ({offerwall}) - {int(points_val)} coins")
                            
            except Exception as e:
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
    print("🤖 ApuCash Live Offer Notifier (Fixed - Real Username)")
    print(f"💰 Minimum Points: {MIN_POINTS}+ coins")
    print(f"⏱ Check Interval: {CHECK_INTERVAL} seconds")
    print("="*60)
    
    # স্টার্ট নোটিফিকেশন
    send_telegram(
        f"✅ <b>ApuCash Notifier চালু হয়েছে!</b>\n\n"
        f"🎯 শুধু <b>{MIN_POINTS}+ coins</b> দেখাবে\n"
        f"👤 আসল ইউজারনেম দেখাবে (xyl20yuh, heleelt ইত্যাদি)\n"
        f"⏱ চেক ইন্টারভাল: {CHECK_INTERVAL} সেকেন্ড"
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
                    
                    # মেসেজ তৈরি - Offerwall নামসহ
                    msg = (
                        f"🟢 <b>New ApuCash Activity!</b>\n\n"
                        f"👤 <b>User:</b> {offer['username']}\n"
                        f"🏢 <b>Offerwall:</b> {offer['offerwall']}\n"
                        f"💰 <b>Points:</b> {offer['points']}\n"
                        f"⏱ <b>Time:</b> {offer['time']}"
                    )
                    
                    if send_telegram(msg):
                        print(f"📨 Sent: {offer['username']} - {offer['points']} ({offer['offerwall']})")
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
