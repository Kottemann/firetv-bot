import requests
from bs4 import BeautifulSoup
import asyncio
import os
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

# Environment Variables
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not TOKEN or not CHANNEL_ID:
    print("❌ TOKEN oder CHANNEL_ID fehlt!")
    exit(1)

bot = Bot(token=TOKEN)

# Preisgrenzen - du kannst diese hier anpassen
PRICE_LIMITS = {
    "Fire TV Stick 4K": 80,
    "Fire TV Stick 4K Plus": 80,
    "Fire TV Stick 4K Max": 80,
    "Fire TV Cube": 150
}

MODELS = {
    "Fire TV Stick 4K": "https://geizhals.de/?fs=fire+tv+stick+4k",
    "Fire TV Stick 4K Plus": "https://geizhals.de/?fs=fire+tv+stick+4k+plus",
    "Fire TV Stick 4K Max": "https://geizhals.de/?fs=fire+tv+stick+4k+max",
    "Fire TV Cube": "https://geizhals.de/?fs=fire+tv+cube"
}

async def get_best_deals():
    print(f"[{datetime.now().strftime('%H:%M')}] Geizhals Suche gestartet...")
    good_deals = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for model, url in MODELS.items():
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            products = soup.find_all('div', class_='productlist__item')[:10]

            for p in products:
                try:
                    name_tag = p.find('a', class_='productlist__link')
                    name = name_tag.get_text(strip=True) if name_tag else model
                    
                    price_tag = p.find('span', class_='productlist__price')
                    price_text = price_tag.get_text(strip=True) if price_tag else ""
                    price = float(price_text.replace('€', '').replace(',', '.').strip()) if price_text else 999
                    
                    limit = PRICE_LIMITS.get(model, 999)
                    
                    if price <= limit:
                        link = "https://geizhals.de" + name_tag['href'] if name_tag else url
                        good_deals.append({
                            "model": model,
                            "name": name[:80],
                            "price": price,
                            "link": link
                        })
                        print(f"   ✅ Guter Deal gefunden: {model} für {price}€")
                except:
                    continue
        except Exception as e:
            print(f"   Fehler bei {model}: {e}")

    # Nur posten, wenn wirklich gute Deals vorhanden sind
    if good_deals:
        print(f"✅ {len(good_deals)} gute Deals gefunden → Posten")
        await bot.send_message(
            chat_id=CHANNEL_ID, 
            text=f"🔥 **Geizhals Fire TV Deals** — {datetime.now().strftime('%d.%m.%Y')}\n\n"
                 f"Gute Angebote gefunden:",
            parse_mode='Markdown'
        )
        
        for deal in good_deals[:3]:   # maximal 3 beste
            msg = f"""🔥 **{deal['model']}**

**{deal['name']}**
💰 **{deal['price']:.2f} €**

🔗 [Jetzt anschauen]({deal['link']})
"""
            await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode='Markdown')
            await asyncio.sleep(2)
    else:
        print("❌ Keine guten Deals unter den Preisgrenzen gefunden.")

async def main():
    scheduler = AsyncIOScheduler(timezone="Europe/Berlin")
    scheduler.add_job(get_best_deals, 'cron', hour=7, minute=0)
    scheduler.start()
    print("Bot gestartet - sucht täglich um 7 Uhr auf Geizhals")
    
    await get_best_deals()   # Sofort-Test

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
