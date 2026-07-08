async def get_best_deals(bot: Bot):
    print(f"[{datetime.now().strftime('%H:%M')}] Geizhals Suche gestartet...")

    deals = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for model, url in MODELS.items():
        try:
            response = requests.get(url, headers=headers, timeout=20)
            print(f"→ {model}: Status {response.status_code}")

            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, "lxml")

            # Neue Struktur: Produkte sind in <h3> oder als ### [ Titel ](
            products = soup.find_all(["h3", "h2", "h1"])  # Überschriften mit Produkten
            print(f"→ {model}: {len(products)} Überschriften gefunden")

            for item in products[:15]:  # Etwas mehr nehmen, da Struktur anders ist
                try:
                    # Link und Name extrahieren
                    link_tag = item.find("a")
                    if not link_tag:
                        continue

                    name = link_tag.get_text(strip=True)
                    if not name or "Fire TV" not in name and model.split()[0] not in name:
                        continue

                    # Preis im nachfolgenden Text suchen
                    price_text = None
                    next_siblings = item.find_next_siblings()
                    for sibling in next_siblings[:6]:  # Preis kommt meist kurz danach
                        text = sibling.get_text()
                        if "€" in text and ("ab" in text or "um" in text or "Angebot" in text):
                            price_text = text
                            break

                    if not price_text:
                        continue

                    # Preis extrahieren
                    import re
                    price_match = re.search(r"€\s*([\d.,]+)", price_text)
                    if not price_match:
                        continue

                    price_clean = price_match.group(1).replace(".", "").replace(",", ".")
                    price = float(price_clean)

                    limit = PRICE_LIMITS.get(model, 999)

                    if price <= limit + 5:
                        full_link = "https://geizhals.de" + link_tag["href"] if link_tag["href"].startswith("/") else link_tag["href"]
                        
                        deals.append({
                            "model": model,
                            "name": name[:90],
                            "price": price,
                            "link": full_link
                        })
                        print(f"✅ Deal: {model} {price:.2f}€ - {name[:60]}")

                except Exception:
                    continue

            await asyncio.sleep(2)

        except Exception as e:
            print(f"Fehler bei {model}: {e}")

    # ---------------------------------------------------------
    # TELEGRAM NACHRICHTEN SENDEN
    # ---------------------------------------------------------
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

        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
            parse_mode="Markdown"
        )
        await asyncio.sleep(2)
