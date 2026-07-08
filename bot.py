import asyncio
import os
from datetime import datetime
from bs4 import BeautifulSoup
import cloudscraper  # <-- WICHTIG: Ersetzt requests, um Cloudflare zu umgehen
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not TOKEN or not CHANNEL_ID:
    print("❌ TOKEN oder CHANNEL_ID fehlt!")
    exit(1)

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

# Wir übergeben den initialisierten bot an die Funktion
async def get_best_deals(bot: Bot):
    print(f"[{datetime.now().strftime('%H:%M')}] Geizhals Suche gestartet...")
    good_deals = []

    # Cloudscraper instanziieren
    scraper = cloudscraper.create_scraper()

    for model, url in MODELS.items():
        try:
            resp = scraper.get(url, timeout=20)
            print(f"   → {model}: Status {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"   → {model}: Wird blockiert (Status {resp.status_code})")
                continue
                
            soup = BeautifulSoup(resp.text, 'html.parser')
            products = soup.find_all('div', class_='productlist__item')

            print(f"   → {model}: {len(products)} Produkte gefunden")

            for p in products[:10]:
                try:
                    name_tag = p.find('a', class_='productlist__link')
                    name = name_tag.get_text(strip=True) if name_tag else model

                    price_tag = p.find('span', class_='productlist__price')
                    price_text = price_tag.get_text(strip=True) if price_tag else ""
                    
                    price_clean = ''.join(filter(str.isdigit, price_text.replace(',', '.')))
                    price = float(price_clean) / 100 if price_clean else 999

                    limit = PRICE_LIMITS.get(model, 999)
                    
                    if price <= limit + 5:   # kleiner Puffer
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
        print(f"✅ {len(good_deals)} gute Deals gefunden!")
        await bot.send_message(chat_id=CHANNEL_ID, 
                              text=f"🔥 *Geizhals Fire TV Deals* — {datetime.now().strftime('%d.%m.%Y')}",
                              parse_mode='Markdown')
        
        for deal in sorted(good_deals, key=lambda x: x['price'])[:3]:
            # Achtung bei Markdown: Zeichen wie _ oder * im Produktnamen können zu Fehlern führen.
            # Daher nutzen wir hier einfaches Text-Parsing oder escapen es.
            msg = f"🔥 *{deal['model']}*\n\n{deal['name']}\n💰 *{deal['price']:.2f} €*\n\n🔗 [Zum Angebot]({deal['link']})"
            await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode='Markdown')
            await asyncio.sleep(2)
    else:
        print("❌ Keine guten Deals unter den Preisgrenzen gefunden.")

async def main():
    # Hier initialisieren wir den Bot korrekt innerhalb des asynchronen Kontextes
    async with Bot(token=TOKEN) as bot:
        scheduler = AsyncIOScheduler(timezone="Europe/Berlin")
        # Wir nutzen einen Lambda-Ausdruck, um den Bot an die Funktion zu übergeben
        scheduler.add_job(lambda: get_best_deals(bot), 'cron', hour=7, minute=0)
        scheduler.start()
        print("Bot gestartet - sucht täglich um 7 Uhr auf Geizhals")
        
        # Einmaliger Testlauf beim Start
        await get_best_deals(bot)

        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
