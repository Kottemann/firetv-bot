import asyncio
import os
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright  # <-- NEU
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

async def get_best_deals(bot: Bot):
    print(f"[{datetime.now().strftime('%H:%M')}] Geizhals Suche via Playwright gestartet...")
    good_deals = []

    # Playwright Browser im Hintergrund starten
    async with async_playwright() as p:
        # Wir nutzen Chromium und tarnen uns als normaler Desktop-Browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        for model, url in MODELS.items():
            try:
                # Seite aufrufen und warten, bis das Netzwerk ruhig ist
                response = await page.goto(url, wait_until="networkidle", timeout=30000)
                status = response.status if response else "Unbekannt"
                print(f"   → {model}: Status {status}")
                
                if status != 200:
                    print(f"   → {model}: Wird blockiert oder nicht erreichbar.")
                    continue
                
                # HTML-Inhalt aus dem echten Browser-Fenster ziehen
                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')
                products = soup.find_all('div', class_='productlist__item')

                print(f"   → {model}: {len(products)} Produkte gefunden")

                for p_item in products[:10]:
                    try:
                        name_tag = p_item.find('a', class_='productlist__link')
                        name = name_tag.get_text(strip=True) if name_tag else model

                        price_tag = p_item.find('span', class_='productlist__price')
                        price_text = price_tag.get_text(strip=True) if price_tag else ""
                        
                        price_clean = ''.join(filter(str.isdigit, price_text.replace(',', '.')))
                        price = float(price_clean) / 100 if price_clean else 999

                        limit = PRICE_LIMITS.get(model, 999)
                        
                        if price <= limit + 5:
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
                
                # Kurze Pause zwischen den Suchanfragen, um menschlicher zu wirken
                await asyncio.sleep(3)
                
            except Exception as e:
                print(f"   Fehler bei {model}: {e}")
        
        await browser.close()

    # Telegram Nachricht senden (unverändert)
    if good_deals:
        print(f"✅ {len(good_deals)} gute Deals gefunden!")
        await bot.send_message(chat_id=CHANNEL_ID, 
                              text=f"🔥 *Geizhals Fire TV Deals* — {datetime.now().strftime('%d.%m.%Y')}",
                              parse_mode='Markdown')
        
        for deal in sorted(good_deals, key=lambda x: x['price'])[:3]:
            msg = f"🔥 *{deal['model']}*\n\n{deal['name']}\n💰 *{deal['price']:.2f} €*\n\n🔗 [Zum Angebot]({deal['link']})"
            await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode='Markdown')
            await asyncio.sleep(2)
    else:
        print("❌ Keine guten Deals unter den Preisgrenzen gefunden.")

async def main():
    async with Bot(token=TOKEN) as bot:
        scheduler = AsyncIOScheduler(timezone="Europe/Berlin")
        scheduler.add_job(lambda: get_best_deals(bot), 'cron', hour=7, minute=0)
        scheduler.start()
        print("Bot gestartet - sucht täglich um 7 Uhr auf Geizhals")
        
        await get_best_deals(bot)

        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
