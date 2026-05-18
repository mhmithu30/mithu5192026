import time
import json
import os
import re
import hashlib
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests

# ================== কনফিগারেশন ==================
BOT_TOKEN = "8760185059:AAElry-u0BYW6ZLiejygJ1UYHcPGMy_vq9s"
CHAT_ID = "6881373105"
MIN_POINTS = 4

APUCASH_URL = "https://apucash.com"
SEEN_FILE = "apucash_seen.json"
CHECK_INTERVAL = 60

def send_telegram(message):
    """টেলিগ্রামে মেসেজ পাঠান"""
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

def create_driver():
    """Selenium WebDriver তৈরি করুন"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # হেডলেস মোড
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"❌ Driver error: {e}")
        return None

def scrape_apucash():
    """Selenium দিয়ে ApuCash থেকে ডাটা সংগ্রহ"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Checking ApuCash...")
    
    driver = create_driver()
    if not driver:
        return []
    
    try:
        # ওয়েবসাইট ওপেন করুন
        driver.get(APUCASH_URL)
        
        # পেজ লোড হওয়ার জন্য অপেক্ষা
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # স্ক্রোল করে আরও কন্টেন্ট লোড করুন
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # পেজের সোর্স পান
        page_source = driver.page_source
        
        offers = []
        
        # সব activity এলিমেন্ট খোঁজা
        try:
            # বিভিন্ন সেলেক্টর চেষ্টা
            selectors = [
                "div.activity-item",
                "div.feed-item", 
                "div.earning-item",
                "div[class*='activity']",
                "div[class*='feed']",
                "div[class*='earning']",
                "div.offer-item"
            ]
            
            elements = []
            for selector in selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"  Found {len(elements)} elements with selector: {selector}")
                    break
            
            if not elements:
                # সব div চেক করুন
                elements = driver.find_elements(By.TAG_NAME, "div")
                print(f"  Checking {len(elements)} div elements...")
            
            for element in elements:
                try:
                    element_text = element.text
                    
                    if len(element_text) < 30:
                        continue
                    
                    # পয়েন্টস খোঁজা
                    points_patterns = [
                        r'(\d{3,})\s*(?:points?|pts?|coins?)',
                        r'[\$](\d{2,}(?:\.\d+)?)',
                        r'(\d+)\s*points',
                        r'reward[:\s]+(\d+)',
                    ]
                    
                    points_val = 0
                    for pattern in points_patterns:
                        match = re.search(pattern, element_text, re.I)
                        if match:
                            raw_points = match.group(1)
                            if '.' in raw_points:
                                points_val = float(raw_points)
                            else:
                                points_val = int(raw_points)
                            break
                    
                    if points_val >= MIN_POINTS:
                        # ইউজারনেম খোঁজা
                        username_patterns = [
                            r'@([A-Za-z][A-Za-z0-9_]{2,20})',
                            r'([A-Za-z][A-Za-z0-9_]{3,20})\s+(?:earned|got|completed)',
                            r'(?:user|username)[:\s]+([A-Za-z][A-Za-z0-9_]{2,20})',
                            r'by\s+([A-Za-z][A-Za-z0-9_]{2,20})',
                            r'([A-Za-z][A-Za-z0-9_]{4,20})',
                        ]
                        
                        username = None
                        for pattern in username_patterns:
                            match = re.search(pattern, element_text, re.I)
                            if match:
                                potential = match.group(1)
                                if not potential.isdigit() and len(potential) > 2:
                                    username = potential
                                    break
                        
                        if username and points_val >= MIN_POINTS:
                            unique_key = hashlib.md5(f"{username}_{points_val}".encode()).hexdigest()
                            
                            offers.append({
                                "username": username[:30],
                                "points": f"{int(points_val)} points",
                                "points_val": points_val,
                                "key": unique_key,
                                "time": datetime.now().strftime("%I:%M %p"),
                                "details": element_text[:100]
                            })
                            print(f"  ✅ {username} - {int(points_val)} points")
                            
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"  Element parsing error: {e}")
        
        # যদি কিছু না পাওয়া যায়, পুরো পেজ টেক্সট থেকে Regex দিয়ে খোঁজা
        if not offers:
            print("  Trying full page regex...")
            text = page_source
            
            patterns = [
                r'@([A-Za-z][A-Za-z0-9_]{2,20}).*?(\d{3,})\s*(?:points?|coins?)',
                r'([A-Za-z][A-Za-z0-9_]{3,20})\s+(?:earned|got|received)\s+(\d{3,})',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.I)
                for username, points in matches:
                    points_val = int(points)
                    if points_val >= MIN_POINTS and len(username) > 2:
                        unique_key = hashlib.md5(f"{username}_{points_val}".encode()).hexdigest()
                        
                        if not any(o['key'] == unique_key for o in offers):
                            offers.append({
                                "username": username[:30],
                                "points": f"{points_val} points",
                                "points_val": points_val,
                                "key": unique_key,
                                "time": datetime.now().strftime("%I:%M %p"),
                                "details": ""
                            })
                            print(f"  ✅ Regex: {username} - {points_val} points")
        
        driver.quit()
        print(f"📊 Total offers: {len(offers)}")
        return offers
        
    except Exception as e:
        print(f"❌ Scraping error: {e}")
        if driver:
            driver.quit()
        return []

def main():
    print("="*60)
    print("🤖 ApuCash Live Offer Notifier (Selenium Version)")
    print(f"💰 Minimum Points: {MIN_POINTS}+")
    print(f"⏱ Check Interval: {CHECK_INTERVAL} seconds")
    print("="*60)
    
    # স্টার্ট নোটিফিকেশন
    send_telegram(
        f"✅ <b>ApuCash Notifier Started!</b>\n\n"
        f"🎯 {MIN_POINTS}+ points only\n"
        f"⏱ Checking every {CHECK_INTERVAL} seconds\n"
        f"🔄 Using Selenium (dynamic content)"
    )
    
    # সিন অফার লোড
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
                    
                    # সিন ফাইল সেভ
                    with open(SEEN_FILE, "w") as f:
                        json.dump(list(seen_offers), f)
                    
                    time.sleep(1)
            
            if len(offers) == 0:
                print("📭 No new offers")
            
        except Exception as e:
            print(f"❌ Main loop error: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
