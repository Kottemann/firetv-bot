import requests
from bs4 import BeautifulSoup
import asyncio
import os
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

# Environment Variables aus Railway lesen
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not TOKEN or not CHANNEL_ID:
    print("❌ TOKEN oder CHANNEL_ID fehlt!")
    exit(1)

bot = Bot(token=TOKEN)

async def get_best_deals():
    print(f"[{datetime.now().strftime('%H:%M')}] Suche gestartet...")
    all_deals = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    }

    models = {
        "Fire TV Stick 4K": "https://www.idealo.de/preisvergleich/ProductCategory/120556008F.html?sortKey=minPrice",
        "Fire TV Stick 4K Plus": "https://www.idealo.de/preisvergleich/OffersOfProduct/208414668_-fire-tv-stick-4k-plus-amazon.html",
        "Fire TV Stick 4K Max": "https://www.idealo.de/preisvergleich/OffersOfProduct/203374258_-fire-tv-stick-4k-max-2-gen-amazon.html",
        "Fire TV Cube": "https://www.idealo.de/preisvergleich/Liste/120556008/fire-tv-cube.html?sortKey=minPrice"
    }

    for model, url in models.items():
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            print(f"   → {model}: Status {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"   → {model}: Seite blockiert oder nicht erreichbar")
                continue
                
            soup = BeautifulSoup(resp.text, 'html.parser')
            offers = soup.find_all('div', class_=lambda x: x and 'offer' in str(x).lower())
            
            print(f"   → {model}: {len(offers)} Angebote gefunden")
            
            for offer in offers[:5]:
                try:
                    name = offer.find(['h2', 'a']).get_text(strip=True) if offer.find(['h2', 'a']) else model
                    price_text = offer.find(class_=lambda x: x and 'price' in str(x).lower())
                    price_text = price_text.get_text(strip=True) if price_text else "0"
                    price = float(''.join(filter(str.isdigit, price_text.replace(',', '.')))) / 100
                    
                    all_deals.append({
                        "model": model,
                        "name": name[:80],
                        "price": price,
                        "total": price,
                        "link": url
                    })
                except:
                    continue
        except Exception as e:
            print(f"   Fehler bei {model}: {e}")

    all_deals.sort(key=lambda x: x['total'])
    best_two = all_deals[:2]

    if best_two:
        print(f"✅ {len(best_two)} Angebote gefunden")
        await bot.send_message(chat_id=CHANNEL_ID, text=f"🕖 **Idealo Fire TV Deals** — {datetime.now().strftime('%d.%m.%Y')}", parse_mode='Markdown')
        for deal in best_two:
            msg = f"""🔥 **{deal['model']}**

**{deal['name']}**
💰 **{deal['price']:.2f} €**

🔗 [Zum Angebot]({deal['link']})
"""
            await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode='Markdown')
    else:
        print("❌ Keine Angebote gefunden")
        await bot.send_message(chat_id=CHANNEL_ID, text=f"🕖 **Idealo Fire TV Suche** — {datetime.now().strftime('%d.%m.%Y')}\n\nMomentan keine guten Angebote gefunden.", parse_mode='Markdown')

async def main():
    scheduler = AsyncIOScheduler(timezone="Europe/Berlin")
    scheduler.add_job(get_best_deals, 'cron', hour=7, minute=0)
    scheduler.start()
    print("Bot gestartet - täglich um 7 Uhr")
    
    await get_best_deals()   # Sofort-Test

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
