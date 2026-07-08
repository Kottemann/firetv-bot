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
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "de-DE,de;q=0.9",
                "Referer": "https://geizhals.de/",
            }

            response = session.get(url, headers=headers, timeout=30)
            print(f"→ {model}: Status {response.status_code}")

            if response.status_code != 200:
                print(f"   ⚠️ Block oder Fehler bei {model}")
                await asyncio.sleep(8)
                continue

            soup = BeautifulSoup(response.text, "lxml")
            products = soup.find_all(["h1", "h2", "h3"])

            print(f"→ {model}: {len(products)} Überschriften gefunden")

            for item in products[:25]:
                try:
                    link_tag = item.find("a", href=True)
                    if not link_tag:
                        continue

                    name = link_tag.get_text(strip=True)
                    if "Fire TV" not in name and "Stick" not in name:
                        continue

                    price_text = None
                    for sib in item.find_next_siblings()[:10]:
                        if "€" in sib.get_text():
                            price_text = sib.get_text()
                            break

                    if not price_text:
                        continue

                    price_match = re.search(r"€\s*([\d.,]+)", price_text)
                    if price_match:
                        price = float(price_match.group(1).replace(".", "").replace(",", "."))
                        if price <= PRICE_LIMITS.get(model, 999) + 10:
                            link = link_tag["href"]
                            if link.startswith("/"):
                                link = "https://geizhals.de" + link
                            deals.append({
                                "model": model,
                                "name": name[:90],
                                "price": price,
                                "link": link
                            })
                            print(f"✅ Deal: {model} {price:.2f}€")
                except:
                    continue

            await asyncio.sleep(random.uniform(4, 8))

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

        print("Bot gestartet - tägliche Suche um 7 Uhr")
        await get_best_deals(bot)   # Testlauf

        while True:
            await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
