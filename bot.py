async def get_best_deals(bot: Bot):
    print(f"[{datetime.now().strftime('%H:%M')}] Geizhals Suche gestartet...")

    deals = []
    session = requests.Session()

    for model, url in MODELS.items():
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://www.google.com/",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            # Längere Wartezeit + Retry
            response = session.get(url, headers=headers, timeout=30)
            print(f"→ {model}: Status {response.status_code}")

            if response.status_code == 403:
                print(f"   ❌ Stark blockiert bei {model}. Überspringe...")
                await asyncio.sleep(10)
                continue

            if response.status_code != 200:
                await asyncio.sleep(5)
                continue

            soup = BeautifulSoup(response.text, "lxml")

            products = soup.find_all(["h1", "h2", "h3"])
            print(f"→ {model}: {len(products)} Überschriften gefunden")

            count = 0
            for item in products[:25]:
                try:
                    link_tag = item.find("a", href=True)
                    if not link_tag:
                        continue

                    name = link_tag.get_text(strip=True)
                    if "Fire TV" not in name and "Stick" not in name and "Cube" not in name:
                        continue

                    # Preis suchen
                    price_text = None
                    for sib in item.find_next_siblings()[:12]:
                        txt = sib.get_text(strip=True)
                        if "€" in txt:
                            price_text = txt
                            break

                    if not price_text:
                        continue

                    price_match = re.search(r"€\s*([\d.,]+)", price_text)
                    if not price_match:
                        continue

                    price = float(price_match.group(1).replace(".", "").replace(",", "."))

                    if price <= PRICE_LIMITS.get(model, 999) + 10:
                        full_link = link_tag["href"]
                        if full_link.startswith("/"):
                            full_link = "https://geizhals.de" + full_link

                        deals.append({
                            "model": model,
                            "name": name[:85],
                            "price": price,
                            "link": full_link
                        })
                        count += 1
                        print(f"✅ Deal: {model} | {price:.2f}€ | {name[:50]}")

                except:
                    continue

            print(f"   → {count} potenzielle Deals bei {model}")

            await asyncio.sleep(random.uniform(6, 11))

        except Exception as e:
            print(f"Fehler bei {model}: {e}")

    # Senden
    if not deals:
        print("❌ Keine guten Deals gefunden.")
        return

    # ... (Rest der Sendelogik bleibt gleich)
    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=f"🔥 *Geizhals Fire TV Deals*\n{datetime.now().strftime('%d.%m.%Y')}",
        parse_mode="Markdown"
    )

    for deal in sorted(deals, key=lambda x: x["price"])[:3]:
        text = f"🔥 *{deal['model']}*\n\n{deal['name']}\n💰 *{deal['price']:.2f} €*\n\n🔗 [Zum Angebot]({deal['link']})"
        await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="Markdown")
        await asyncio.sleep(2)
