import requests
from bs4 import BeautifulSoup
import asyncio
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

TOKEN = "DEIN_TOKEN_HIER_EINFÜGEN"
CHANNEL_ID = "@DEIN_KANAL_NAME"   # z.B. @firetvdeals

MODELS = {
    "Fire TV Stick 4K": "https://www.idealo.de/preisvergleich/ProductCategory/120556008F.html?sortKey=minPrice",
    "Fire TV Stick 4K Plus": "https://www.idealo.de/preisvergleich/OffersOfProduct/208414668_-fire-tv-stick-4k-plus-amazon.html",
    "Fire TV Stick 4K Max": "https://www.idealo.de/preisvergleich/OffersOfProduct/203374258_-fire-tv-stick-4k-max-2-gen-amazon.html",
    "Fire TV Cube": "https://www.idealo.de/preisvergleich/Liste/120556008/fire-tv-cube.html?sortKey=minPrice"
}

bot = Bot(token=TOKEN)

async def get_best_deals():
    print("Suche gestartet...")
    all_deals = []
    headers = {"User-Agent": "Mozilla/5.0"}

    for model, url in MODELS.items():
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            offers = soup.find_all(['div', 'article'], class_=['offerList__item', 'productOffer'])[:10]

            for offer in offers:
                try:
                    name = offer.find(['a', 'h2'], class_=['offerList__productName', 'productName'])
                    name = name.get_text(strip=True)[:80] if name else model

                    price_tag = offer.find(['span', 'strong'], class_=['offerList__price', 'price'])
                    price_text = price_tag.get_text(strip=True) if price_tag else ""
                    price = float(price_text.replace('€', '').replace(',', '.').replace('*','').strip()) if price_text else 999

                    shipping = 0
                    if "kostenlos" in str(offer).lower():
                        shipping = 0

                    total = price + shipping
                    link = offer.find('a', href=True)
                    link = "https://www.idealo.de" + link['href'] if link else url

                    all_deals.append({"model": model, "name": name, "price": price, "shipping": shipping, "total": total, "link": link})
                except:
                    continue
        except:
            continue

    all_deals.sort(key=lambda x: x['total'])
    best_two = all_deals[:2]

    if best_two:
        await bot.send_message(chat_id=CHANNEL_ID, text=f"🕖 **Idealo Fire TV Deals** — {datetime.now().strftime('%d.%m.%Y')}", parse_mode='Markdown')
        for deal in best_two:
            shipping_str = "Versandkostenfrei" if deal['shipping'] == 0 else f"+ {deal['shipping']:.2f}€ Versand"
            msg = f"""🔥 **{deal['model']}**

**{deal['name']}**
💰 **{deal['price']:.2f} €**
📦 {shipping_str}
**Gesamt ≈ {deal['total']:.2f} €**

🔗 [Zum Angebot]({deal['link']})
"""
            await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode='Markdown')
            await asyncio.sleep(2)

async def main():
    scheduler = AsyncIOScheduler(timezone="Europe/Berlin")
    scheduler.add_job(get_best_deals, 'cron', hour=7, minute=0)
    scheduler.start()
    print("Bot gestartet - täglich um 7 Uhr")
    await get_best_deals()  # Test

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
