Ersetze in deiner `bot.py`:

1. Diese Zeile löschen:

```python
from playwright.async_api import async_playwright
```

2. Diese Zeile hinzufügen:

```python
import requests
```

3. Die komplette Funktion `get_best_deals()` durch diese ersetzen:

```python
async def get_best_deals(bot: Bot):
    print(f"[{datetime.now().strftime('%H:%M')}] Geizhals Suche gestartet...")
    good_deals = []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0 Safari/537.36"
        )
    }

    for model, url in MODELS.items():
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=20
            )

            print(f"→ {model}: Status {response.status_code}")

            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, "lxml")
            products = soup.find_all("div", class_="productlist__item")

            print(f"→ {model}: {len(products)} Produkte gefunden")

            for p_item in products[:10]:
                try:
                    name_tag = p_item.find(
                        "a",
                        class_="productlist__link"
                    )

                    if not name_tag:
                        continue

                    name = name_tag.get_text(strip=True)

                    price_tag = p_item.find(
                        "span",
                        class_="productlist__price"
                    )

                    if not price_tag:
                        continue

                    price_text = price_tag.get_text(strip=True)

                    price_clean = (
                        price_text
                        .replace("€", "")
                        .replace(".", "")
                        .replace(",", ".")
                        .strip()
                    )

                    try:
                        price = float(price_clean)
                    except:
                        continue

                    limit = PRICE_LIMITS.get(model, 999)

                    if price <= limit + 5:
                        link = (
                            "https://geizhals.de"
                            + name_tag["href"]
                        )

                        good_deals.append({
                            "model": model,
                            "name": name[:90],
                            "price": price,
                            "link": link
                        })

                        print(
                            f"✅ Guter Deal: "
                            f"{model} für {price:.2f} €"
                        )

                except Exception as e:
                    print(
                        f"Fehler beim Produkt: {e}"
                    )

            await asyncio.sleep(2)

        except Exception as e:
            print(f"Fehler bei {model}: {e}")

    if good_deals:
        print(
            f"✅ {len(good_deals)} gute Deals gefunden!"
        )

        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=(
                f"🔥 *Geizhals Fire TV Deals* — "
                f"{datetime.now().strftime('%d.%m.%Y')}"
            ),
            parse_mode="Markdown"
        )

        for deal in sorted(
            good_deals,
            key=lambda x: x["price"]
        )[:3]:

            msg = (
                f"🔥 *{deal['model']}*\n\n"
                f"{deal['name']}\n"
                f"💰 *{deal['price']:.2f} €*\n\n"
                f"🔗 [Zum Angebot]({deal['link']})"
            )

            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=msg,
                parse_mode="Markdown"
            )

            await asyncio.sleep(2)

    else:
        print(
            "❌ Keine guten Deals unter den Preisgrenzen gefunden."
        )
```

4. Den Scheduler ändern:

Ersetze:

```python
scheduler.add_job(
    lambda: get_best_deals(bot),
    'cron',
    hour=7,
    minute=0
)
```

durch:

```python
scheduler.add_job(
    lambda: asyncio.create_task(
        get_best_deals(bot)
    ),
    'cron',
    hour=7,
    minute=0
)
```
