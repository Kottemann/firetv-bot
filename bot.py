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

MODELS = {
    "Fire TV Stick 4K": "https://geizhals.de/?fs=fire+tv+stick+4k",
    "Fire TV Stick 4K Plus": "https://geizhals.de/?fs=fire+tv+stick+4k+plus",
    "Fire TV Stick 4K Max": "https://geizhals.de/?fs=fire+tv+stick+4k+max",
    "Fire TV Cube": "https://geizhals.de/?fs=fire+tv+cube"
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
# GEIZHALS SCRAPER
# -------------------------------------------------------------
async def get_best_deals(bot: Bot):
    print(f"[{datetime.now().strftime('%H:%M')}] Geizhals Suche gestartet...")

    deals = []
    session = requests.Session()

    for model, url in MODELS.items():
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }

            response = session.get(url, headers=headers, timeout=25)
            print(f"→ {model}: Status {response.status_code}")

            if response.status_code != 200:
                print(f"   ⚠️ Blockiert ({response.status_code})")
                await asyncio.sleep(10)
                continue

            soup = BeautifulSoup(response.text, "lxml")

            # Einfache Preissuche
            price_match = re.search(r"€\s*(\d{2,4})[.,](\d{2})", response.text)
            if price_match:
                price = float(price_match.group(1) + "." + price_match.group(2))
                print(f"   → Gefundener Preis: {price:.2f}€")

                if price <= PRICE_LIMITS.get(model, 999) + 10:
                    deals.append({
                        "model": model,
                        "name": model,
                        "price": price,
                        "link": url
                    })
                    print(f"✅ Deal: {model} {price:.2f}€")
            else:
                print(f"   → Kein Preis gefunden")

            await asyncio.sleep(random.uniform(6, 12))

        except Exception as e:
            print(f"Fehler bei {model}: {e}")

    if not deals:
        print("❌ Keine guten Deals gefunden.")
        return

    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=f"🔥 *Geizhals Fire TV Deals*\n{datetime.now().strftime('%d.%m.%Y')}",
        parse_mode="Markdown"
    )

    for deal in sorted(deals, key=lambda x: x["price"]):
        text = f"🔥 *{deal['model']}*\n💰 *{deal['price']:.2f} €*\n🔗 [Zum Angebot]({deal['link']})"
        await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="Markdown")
        await asyncio.sleep(2)


# -------------------------------------------------------------
# START
# -------------------------------------------------------------
async def main():
    threading.Thread(target=run_health_server, daemon=True).start()

    async with Bot(token=TOKEN) as bot:
        print("Bot gestartet - erste Suche läuft...")

        await get_best_deals(bot)  # Testlauf

        scheduler = AsyncIOScheduler(timezone="Europe/Berlin")
        scheduler.add_job(
            lambda: asyncio.create_task(get_best_deals(bot)),
            "cron",
            hour=7,
            minute=0
        )
        scheduler.start()

        print("Scheduler aktiv (täglich 7 Uhr)")

        while True:
            await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
