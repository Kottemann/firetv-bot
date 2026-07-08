import requests
from bs4 import BeautifulSoup
import asyncio
import os
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not TOKEN or not CHANNEL_ID:
    print("❌ TOKEN oder CHANNEL_ID fehlt!")
    exit(1)

bot = Bot(token=TOKEN)

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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    }

    for model, url in MODELS.items():
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            print(f"   → {model}: Status {resp.status_code}")
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            products = soup.find_all('div', class_='productlist__item')

            print(f"   → {model}: {len(products)} Produkte gefunden")

            for p in products[:12]:
                try:
                    name_tag = p.find('a', class_='productlist__link')
                    name = name_tag.get_text(strip=True) if name_tag else model

                    # Preis extrahieren (verschiedene mögliche Klassen)
                    price_tag = p.find('span', class_='productlist__price') or p.find('span', class_=lambda x: x and 'price' in str(x).lower())
                    price_text = price_tag.get_text(strip=True) if price_tag else ""
                    
                    # Preis sauber machen
                    price_clean = ''.join(filter(str.isdigit, price_text.replace(',', '.')))
                    price = float(price_clean) / 100 if price_clean else 999

                    limit = PRICE_LIMITS.get(model, 999)
                    
                    if price <= limit:
                        link = "https://geizhals.de" + name_tag['href'] if name_tag else url
                        good_deals.append({
                            "model": model,
                            "name": name[:90],
                            "price": price,
                            "link": link
                        })
                        print(f"   ✅ Guter Deal: {model} für {price:.2f}€")
                except:
                    continue
        except Exception as e:
            print(f"   Fehler bei {model}: {e}")

    if good_deals:
        print(f"✅ {len(good_deals)} gute Deals gefunden → Posten in Kanal")
        await bot.send_message(chat_id=CHANNEL_ID, 
                              text=f"🔥 **Geizhals Fire TV Deals** — {datetime.now().strftime('%d.%m.%Y')}\n",
                              parse_mode='Markdown')
        
        for deal in sorted(good_deals, key=lambda x: x['price'])[:3]:
            msg = f"""🔥 **{deal['model']}**

**{deal['name']}**
💰 **{deal['price']:.2f} €**

🔗 [Zum Angebot]({deal['link']})
"""
            await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode='Markdown')
            await asyncio.sleep(2)
    else:
        print("❌ Keine Deals unter den Preisgrenzen gefunden.")

async def main():
    scheduler = AsyncIOScheduler(timezone="Europe/Berlin")
    scheduler.add_job(get_best_deals, 'cron', hour=7, minute=0)
    scheduler.start()
    print("Bot gestartet - sucht täglich um 7 Uhr auf Geizhals")
    
    await get_best_deals()  # Sofort-Test

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
