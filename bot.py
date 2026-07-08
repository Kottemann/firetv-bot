```python
import asyncio
import os
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
# RAILWAY HEALTH CHECK
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

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthCheckHandler
    )

    print(f"[System] Health Check läuft auf Port {port}")

    server.serve_forever()



# -------------------------------------------------------------
# GEIZHALS SCRAPER
# -------------------------------------------------------------

async def get_best_deals(bot: Bot):

    print(
        f"[{datetime.now().strftime('%H:%M')}] "
        "Geizhals Suche gestartet..."
    )


    deals = []


    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }


    for model, url in MODELS.items():

        try:

            response = requests.get(
                url,
                headers=headers,
                timeout=20
            )


            print(
                f"→ {model}: Status {response.status_code}"
            )


            if response.status_code != 200:
                continue


            soup = BeautifulSoup(
                response.text,
                "lxml"
            )


            products = soup.find_all(
                "div",
                class_="productlist__item"
            )


            print(
                f"→ {model}: {len(products)} Produkte gefunden"
            )


            for item in products[:10]:

                try:

                    name_tag = item.find(
                        "a",
                        class_="productlist__link"
                    )


                    price_tag = item.find(
                        "span",
                        class_="productlist__price"
                    )


                    if not name_tag or not price_tag:
                        continue


                    name = name_tag.get_text(
                        strip=True
                    )


                    price_text = price_tag.get_text(
                        strip=True
                    )


                    price_clean = (
                        price_text
                        .replace("€", "")
                        .replace(".", "")
                        .replace(",", ".")
                        .strip()
                    )


                    price = float(price_clean)


                    limit = PRICE_LIMITS.get(
                        model,
                        999
                    )


                    if price <= limit + 5:

                        link = (
                            "https://geizhals.de"
                            + name_tag["href"]
                        )


                        deals.append({

                            "model": model,
                            "name": name[:90],
                            "price": price,
                            "link": link

                        })


                        print(
                            f"✅ Deal: {model} "
                            f"{price:.2f}€"
                        )


                except Exception:
                    continue



            await asyncio.sleep(2)



        except Exception as e:

            print(
                f"Fehler bei {model}: {e}"
            )



    # ---------------------------------------------------------
    # TELEGRAM SENDEN
    # ---------------------------------------------------------

    if not deals:

        print(
            "❌ Keine guten Deals gefunden."
        )

        return



    await bot.send_message(

        chat_id=CHANNEL_ID,

        text=(
            "🔥 *Geizhals Fire TV Deals*\n"
            f"{datetime.now().strftime('%d.%m.%Y')}"
        ),

        parse_mode="Markdown"

    )



    for deal in sorted(
        deals,
        key=lambda x: x["price"]
    )[:3]:


        text = (

            f"🔥 *{deal['model']}*\n\n"
            f"{deal['name']}\n"
            f"💰 *{deal['price']:.2f} €*\n\n"
            f"🔗 [Zum Angebot]({deal['link']})"

        )


        await bot.send_message(

            chat_id=CHANNEL_ID,

            text=text,

            parse_mode="Markdown"

        )


        await asyncio.sleep(2)




# -------------------------------------------------------------
# START
# -------------------------------------------------------------

async def main():


    threading.Thread(
        target=run_health_server,
        daemon=True
    ).start()



    async with Bot(token=TOKEN) as bot:


        scheduler = AsyncIOScheduler(
            timezone="Europe/Berlin"
        )


        scheduler.add_job(

            lambda: asyncio.create_task(
                get_best_deals(bot)
            ),

            "cron",

            hour=7,

            minute=0

        )


        scheduler.start()


        print(
            "Bot gestartet - tägliche Suche um 7 Uhr"
        )


        # Testlauf beim Start

        await get_best_deals(bot)



        while True:

            await asyncio.sleep(3600)



if __name__ == "__main__":

    asyncio.run(main())
```
