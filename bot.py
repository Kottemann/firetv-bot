import asyncio
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# -------------------------------------------------------------
# 1. KONFIGURATION & UMGEBUNGSVARIABLEN
# -------------------------------------------------------------
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

# -------------------------------------------------------------
# 2. RAILWAY HEALTH-CHECK SERVER (Verhindert den "Crashed" Status)
# -------------------------------------------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
        
    def log_message(self, format, *args):
        return  # Verhindert, dass die Logs mit Healthchecks zugespammt werden

def run_health_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"[System] Health-Check-Server läuft auf Port {port}")
    server.serve_forever()

# -------------------------------------------------------------
# 3. SCRAPER & TELEGRAM LOGIK
# -------------------------------------------------------------
async def get_best_deals(bot: Bot):
    print(f"[{datetime.now().strftime('%H:%M')}] Geizhals Suche via Playwright gestartet...")
    good_deals = []

    async with async_playwright() as p:
        # Chromium Headless starten
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        for model, url in MODELS.items():
            try:
                # Seite aufrufen und warten, bis geladen
                response = await page.goto(url, wait_until="networkidle", timeout=30000)
                status = response.status if response else "Unbekannt"
                print(f"   → {model}: Status {status}")
                
                if status != 200:
                    print(f"   → {model}: Wird blockiert oder nicht erreichbar.")
                    continue
                
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
                
                # Kurze Pause, um defensiv zu scrapen
                await asyncio.sleep(3)
                
            except Exception as e:
                print(f"   Fehler bei {model}: {e}")
        
        await browser.close()

    # Deals per Telegram senden
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

# -------------------------------------------------------------
# 4. MAIN SCHLEIFE
# -------------------------------------------------------------
async def main():
    # 1. Den Health-Check-Server für Railway in einem parallelen Thread starten
    threading.Thread(target=run_health_server, daemon=True).start()

    # 2. Den Telegram Bot asynchron initialisieren
    async with Bot(token=TOKEN) as bot:
        scheduler = AsyncIOScheduler(timezone="Europe/Berlin")
        # Täglich um 7:00 Uhr ausführen
        scheduler.add_job(lambda: get_best_deals(bot), 'cron', hour=7, minute=0)
        scheduler.start()
        print("Bot erfolgreich gestartet - sucht täglich um 7 Uhr auf Geizhals")
        
        # Sofortiger Testlauf beim App-Start
        await get_best_deals(bot)

        # Endlosschleife, um den Container aktiv zu halten
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
