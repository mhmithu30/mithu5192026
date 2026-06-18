import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import json
from datetime import datetime
import logging
import asyncio
import re
from bs4 import BeautifulSoup
import time

# ===== লগিং সেটআপ =====
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== কনফিগারেশন =====
TELEGRAM_TOKEN = "8620183702:AAFPVSoom1_PC2lPQzw3rldIzvn25TIJYw8"
CHAT_ID = "6881373105"
GEMIWALL_URL = "https://gemiwall.com/696cb426abfc445d01fefa53/mrpoint8/"

# ===== Socks5 প্রক্সি সেটিংস =====
USE_PROXY = True
PROXY_URL = 'socks5://mimi_seYL-country-US-isp-as701_verizon_business-ssid-XjBoEHoVOt:mimi@niceproxy.io:17522'

# ===== প্রক্সি টেস্ট =====
def test_proxy():
    try:
        logger.info("🔍 Testing Socks5 Proxy...")
        session = requests.Session()
        session.proxies = {
            'http': PROXY_URL,
            'https': PROXY_URL
        }
        response = session.get("http://ip-api.com/json/", timeout=15)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Proxy Working!")
            logger.info(f"📍 IP: {data.get('query')}")
            logger.info(f"🌍 Country: {data.get('country')}")
            logger.info(f"🏙️ City: {data.get('city')}")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Proxy Error: {e}")
        return False

# ===== অফার ফেচ (সঠিক পার্সিং) =====
def fetch_offers_sync():
    """GemiWall থেকে অফার সংগ্রহ করুন"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    
    session = requests.Session()
    if USE_PROXY:
        session.proxies = {
            'http': PROXY_URL,
            'https': PROXY_URL
        }
    
    offers = []
    
    try:
        logger.info(f"🔄 Fetching offers from GemiWall...")
        response = session.get(GEMIWALL_URL, headers=headers, timeout=30)
        
        if response.status_code == 200:
            logger.info(f"✅ Page loaded successfully")
            
            # BeautifulSoup দিয়ে HTML পার্স
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # আপনার স্ক্রিনশটের মতো অফার খুঁজুন
            # এলিমেন্ট গুলো খুঁজুন
            offer_containers = soup.find_all(['div', 'li', 'article'], 
                class_=lambda c: c and any(x in str(c).lower() for x in ['offer', 'item', 'card', 'box', 'task', 'reward'])
            )
            
            if not offer_containers:
                # অন্য সিলেক্টর
                offer_containers = soup.select('.offer-item, .offer-card, .offer, .item, .task-item, .reward-item')
            
            # যদি না পায়, সব লিংক খুঁজুন
            if not offer_containers:
                all_links = soup.find_all('a')
                for link in all_links:
                    text = link.text.strip()
                    if text and len(text) > 3 and len(text) < 100:
                        parent = link.parent
                        if parent:
                            # রিওয়ার্ড খুঁজুন (Points, Pts, etc.)
                            reward_text = ""
                            siblings = parent.find_all(['span', 'div', 'small'])
                            for sib in siblings:
                                if 'point' in sib.text.lower() or 'pts' in sib.text.lower() or '+' in sib.text:
                                    reward_text = sib.text.strip()
                                    break
                            
                            if reward_text:
                                offers.append({
                                    'name': text[:60],
                                    'reward': reward_text,
                                    'link': link.get('href', '#'),
                                    'description': 'Offer from GemiWall'
                                })
            
            # কন্টেইনার থেকে অফার পার্স
            for container in offer_containers:
                try:
                    # নাম খুঁজুন
                    name_elem = container.find(['h3', 'h4', 'div', 'span', 'a'], 
                        class_=lambda c: c and any(x in str(c).lower() for x in ['name', 'title', 'offer'])
                    )
                    if not name_elem:
                        name_elem = container.find(['h3', 'h4', 'strong', 'b'])
                    if not name_elem:
                        name_elem = container.find('a')
                    
                    # রিওয়ার্ড খুঁজুন
                    reward_elem = container.find(['span', 'div'], 
                        class_=lambda c: c and any(x in str(c).lower() for x in ['reward', 'points', 'price', 'coin', 'pts'])
                    )
                    if not reward_elem:
                        # Points প্যাটার্ন খুঁজুন
                        all_text = container.get_text()
                        points_match = re.search(r'[\+\d.]+[Kk]?\s*(?:Points|Pts|points|pts)', all_text, re.I)
                        if points_match:
                            reward_text = points_match.group()
                        else:
                            reward_text = "Check offer"
                    else:
                        reward_text = reward_elem.text.strip()
                    
                    # লিংক
                    link_elem = container.find('a')
                    link = link_elem.get('href') if link_elem else '#'
                    
                    # নাম
                    name = name_elem.text.strip() if name_elem else "Unknown Offer"
                    
                    if name and len(name) > 2:
                        offers.append({
                            'name': name[:60],
                            'reward': reward_text if reward_text else "Check offer",
                            'link': link,
                            'description': 'Offer from GemiWall'
                        })
                except Exception as e:
                    continue
            
            # ডুপ্লিকেট রিমুভ
            seen = set()
            unique_offers = []
            for offer in offers:
                key = offer['name'] + offer['reward']
                if key not in seen:
                    seen.add(key)
                    unique_offers.append(offer)
            
            logger.info(f"📦 Found {len(unique_offers)} unique offers")
            return unique_offers
            
        else:
            logger.error(f"❌ HTTP Error {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"❌ Fetch Error: {e}")
        return []
    finally:
        session.close()

# ===== ফাইল ম্যানেজমেন্ট =====
OFFERS_FILE = "offers_data.json"

def load_offers():
    try:
        with open(OFFERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {"all_offers": [], "sent_offers": []}

def save_offers(data):
    with open(OFFERS_FILE, "w") as f:
        json.dump(data, f)

# ===== টেলিগ্রাম হ্যান্ডলার =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *GemiWall Scraper Bot*\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🟢 *Commands:*\n"
        "/new - Check new offers\n"
        "/all - Get all offers\n"
        "/status - Bot status\n"
        "/refresh - Force refresh offers\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"📍 Proxy: {'ON' if USE_PROXY else 'OFF'}",
        parse_mode="Markdown"
    )

async def new_offers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔍 Searching for new offers...")
    offers = fetch_offers_sync()
    
    if offers:
        await msg.edit_text(f"✅ Found {len(offers)} offers! Showing first 5:")
        for offer in offers[:5]:
            msg_text = (
                f"🎯 *{offer.get('name', 'Unknown')}*\n"
                f"💰 Reward: {offer.get('reward', 'N/A')}\n"
                f"🔗 [View Offer]({offer.get('link', '#')})"
            )
            await update.message.reply_text(msg_text, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        await msg.edit_text("❌ No offers found. Try /refresh to reload.")

async def all_offers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("📋 Fetching all offers...")
    offers = fetch_offers_sync()
    
    if offers:
        await msg.edit_text(f"📋 Total Offers: {len(offers)}")
        
        for i in range(0, min(len(offers), 20), 5):
            batch = offers[i:i+5]
            msg_text = "*📋 Offers List*\n\n" + "\n\n".join([
                f"🎯 {o.get('name', 'Unknown')}\n💰 {o.get('reward', 'N/A')}" 
                for o in batch
            ])
            await update.message.reply_text(msg_text, parse_mode="Markdown")
    else:
        await msg.edit_text("❌ No offers available. Try /refresh.")

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔄 Refreshing offers...")
    offers = fetch_offers_sync()
    
    if offers:
        await msg.edit_text(f"✅ Refreshed! Found {len(offers)} offers")
    else:
        await msg.edit_text("❌ No offers found. Please try again later.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    proxy_status = "🟢 ON" if USE_PROXY else "🔴 OFF"
    await update.message.reply_text(
        f"📊 *Bot Status*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🔄 Status: Running\n"
        f"🌐 Proxy: {proxy_status}\n"
        f"📍 IP: 68.132.64.59 (USA)\n"
        f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"⚡ Engine: BeautifulSoup 4\n"
        f"🔄 Use /refresh to reload offers",
        parse_mode="Markdown"
    )

# ===== শিডিউল টাস্ক =====
async def scheduled_check(context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info("⏰ Running scheduled check...")
        offers = fetch_offers_sync()
        
        if offers:
            data = load_offers()
            new_offers_list = []
            
            for offer in offers:
                offer_id = offer.get('name', '') + offer.get('reward', '')
                if offer_id not in data.get('all_offers', []):
                    new_offers_list.append(offer)
                    data['all_offers'].append(offer_id)
            
            if new_offers_list:
                save_offers(data)
                await context.bot.send_message(
                    chat_id=CHAT_ID, 
                    text=f"🆕 *New Offers Found!*\nTotal: {len(new_offers_list)} new offers"
                )
                for offer in new_offers_list[:3]:
                    msg = f"🎯 {offer.get('name', 'Unknown')}\n💰 {offer.get('reward', 'N/A')}"
                    await context.bot.send_message(chat_id=CHAT_ID, text=msg)
            else:
                logger.info("✅ No new offers found")
        else:
            logger.warning("❌ Could not fetch offers")
            
    except Exception as e:
        logger.error(f"Schedule error: {e}")

# ===== মেইন ফাংশন =====
def main():
    logger.info("🚀 Starting GemiWall Bot...")
    
    if USE_PROXY:
        test_proxy()
    
    # Application তৈরি
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # হ্যান্ডলার যোগ
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("new", new_offers))
    application.add_handler(CommandHandler("all", all_offers))
    application.add_handler(CommandHandler("refresh", refresh))
    application.add_handler(CommandHandler("status", status))
    
    # শিডিউলার (প্রতি ৩০ মিনিট)
    if application.job_queue:
        application.job_queue.run_repeating(scheduled_check, interval=1800, first=30)
        logger.info("✅ Scheduler started (30 min interval)")
    
    # Webhook ডিলিট - Conflict Fix
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(application.bot.delete_webhook(drop_pending_updates=True))
        logger.info("✅ Webhook cleared")
    except Exception as e:
        logger.warning(f"Webhook delete warning: {e}")
    
    logger.info("🤖 Bot is running!")
    
    # Polling শুরু - timeout কমিয়ে Conflict এড়ান
    application.run_polling(
        poll_interval=0.5,
        timeout=20,
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"]
    )

if __name__ == "__main__":
    main()
