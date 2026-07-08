import asyncio
import os
import random
import re
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from bs4 import BeautifulSoup
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler


# -------------------------------------------------------------
# KONFIGURATION
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

# Idealo Such-Links
MODELS = {
    "Fire TV Stick 4K": "https://www.idealo.de/preisvergleich/OffersOfProduct/202020202.html",
    "Fire TV Stick 4K Plus": "https://www.idealo.de/preisvergleich/OffersOfProduct/202030303.html",
    "Fire TV Stick 4K Max": "https://www.idealo.de/preisvergleich/OffersOfProduct/202040404.html",
    "Fire TV Cube": "https://www.idealo.de/preisvergleich/OffersOfProduct/201919191.html"
}


# -------------------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def log_message(self, format, *args):
        return


def run_health_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"[System] Health Check läuft auf Port {port}")
    server.serve_forever()


# -------------------------------------------------------------
# IDEALO SCRAPER
# -------------------------------------------------------------
async def get_best_deals(bot: Bot):
    print(f"[{datetime.now().strftime('%H:%M')}] Idealo Fire TV Suche gestartet...")

    deals = []
    session = requests.Session()

    for model, url in MODELS.items():
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }

            response = session.get(url, headers=headers, timeout=20)
            print(f"→ {model}: Status {response.status_code}")

            if response.status_code != 200:
                print(f"   ⚠️ Konnte {model} nicht laden")
                await asyncio.sleep(6)
                continue

            soup = BeautifulSoup(response.text, "lxml")

            # Preise auf Idealo finden
            price_tags = soup.find_all("span", class_=["price", "product-offer__price", "offer-price"])
            found = False

            for tag in price_tags[:10]:
                try:
                    price_text = tag.get_text(strip=True)
                    match = re.search(r"[\d.,]+", price_text)
                    if match:
                        price_str = match.group(0).replace(".", "").replace(",", ".")
                        price = float(price_str)

                        if price <= PRICE_LIMITS.get(model, 999) + 10:
                            # Produktname
                            name_tag = soup.find("h1") or soup.find("title")
                            name = name_tag.get_text(strip=True)[:90] if name_tag else model

                            link_tag = tag.find_parent("a") or soup.find("a", href=True)
                            link = "https://www.idealo.de" + link_tag["href"] if link_tag and link_tag.get("href") else url

                            deals.append({
                                "model": model,
                                "name": name,
                                "price": price,
                                "link": link
                            })
                            print(f"✅ Guter Deal: {model} für {price:.2f}€")
                            found = True
                            break
                except:
                    continue

            if not found:
                print(f"→ {model}: Kein passender Preis gefunden")

            await asyncio.sleep(random.uniform(4, 8))

        except Exception as e:
            print(f"Fehler bei {model}: {e}")

    if not deals:
        print("❌ Keine guten Deals gefunden.")
        return

    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=f"🔥 *Idealo Fire TV Deals*\n{datetime.now().strftime('%d.%m.%Y')}",
        parse_mode="Markdown"
    )

    for deal in sorted(deals, key=lambda x: x["price"])[:3]:
        text = (
            f"🔥 *{deal['model']}*\n\n"
            f"{deal['name']}\n"
            f"💰 *{deal['price']:.2f} €*\n\n"
            f"🔗 [Zum Angebot]({deal['link']})"
        )
        await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="Markdown")
        await asyncio.sleep(2)


# -------------------------------------------------------------
# START
# -------------------------------------------------------------
async def main():
    threading.Thread(target=run_health_server, daemon=True).start()

    async with Bot(token=TOKEN) as bot:
        scheduler = AsyncIOScheduler(timezone="Europe/Berlin")
        scheduler.add_job(
            lambda: asyncio.create_task(get_best_deals(bot)),
            "cron",
            hour=7,
            minute=0
        )
        scheduler.start()

        print("Bot gestartet - tägliche Idealo-Suche um 7 Uhr")
        await get_best_deals(bot)

        while True:
            await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
