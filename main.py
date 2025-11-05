
#!/usr/bin/env python3
"""
Sports Arbitrage Finder -> Telegram alerts
Author: ChatGPT
Python 3.10+
"""
import asyncio
import os
import time
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
from utils.telegram import TelegramClient
from providers.theoddsapi import TheOddsAPI
from utils.arbitrage import find_arbs_for_event, format_arb_message

DEFAULT_SPORTS = os.getenv("SPORTS", "soccer_epl,basketball_nba,icehockey_nhl,tennis_atp_singles").split(",")
DEFAULT_REGIONS = os.getenv("REGIONS", "eu,uk,us,au").split(",")
DEFAULT_MARKETS = os.getenv("MARKETS", "h2h").split(",")  # moneyline / 1x2
MIN_EDGE_PCT = float(os.getenv("MIN_EDGE_PCT", "0.5"))    # minimum guaranteed edge to alert, e.g., 0.5%
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "120"))      # frequency to poll API
BOOKMAKER_WHITELIST = set([b.strip().lower() for b in os.getenv("BOOKMAKER_WHITELIST", "").split(",") if b.strip()])

# Announce start
def banner() -> str:
    return (
        "🏁 Sports Arbitrage Bot started\n"
        f"Sports: {DEFAULT_SPORTS}\n"
        f"Regions: {DEFAULT_REGIONS}\n"
        f"Markets: {DEFAULT_MARKETS}\n"
        f"Min edge %: {MIN_EDGE_PCT} | Poll: {POLL_SECONDS}s\n"
        f"Whitelist: {sorted(BOOKMAKER_WHITELIST) if BOOKMAKER_WHITELIST else 'ALL'}"
    )

async def scan_once(odds_api: TheOddsAPI, tg: TelegramClient) -> int:
    """Scan once and send alerts. Returns count of alerts sent."""
    alerts = 0
    for sport in DEFAULT_SPORTS:
        try:
            events = await odds_api.fetch_odds(
                sport_key=sport,
                regions=",".join(DEFAULT_REGIONS),
                markets=",".join(DEFAULT_MARKETS),
            )
        except Exception as e:
            await tg.log(f"⚠️ Ошибка запроса API по {sport}: {e}")
            continue

        for ev in events:
            try:
                arbs = find_arbs_for_event(ev, min_edge_pct=MIN_EDGE_PCT, bookmaker_whitelist=BOOKMAKER_WHITELIST)
            except Exception as e:
                await tg.log(f"⚠️ Ошибка расчёта по событию {ev.get('id','?')}: {e}")
                continue

            for arb in arbs:
                msg = format_arb_message(arb)
                await tg.send(msg)
                alerts += 1
    return alerts

async def main():
    load_dotenv()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    api_key = os.getenv("THEODDS_API_KEY")

    if not bot_token or not chat_id:
        raise SystemExit("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
    if not api_key:
        raise SystemExit("Please set THEODDS_API_KEY in .env (get one at https://theoddsapi.com/)")

    tg = TelegramClient(bot_token=bot_token, chat_id=chat_id)
    odds_api = TheOddsAPI(api_key=api_key, timeout=int(os.getenv("HTTP_TIMEOUT", "20")))

    await tg.log("✅ Бот запущен. " + banner())

    # Immediate scan once
    try:
        count = await scan_once(odds_api, tg)
        if count == 0:
            await tg.log("ℹ️ Пока арбитраж не найден. Буду проверять дальше.")
    except Exception as e:
        await tg.log(f"❌ Ошибка первичного сканирования: {e}")

    # Loop
    while True:
        started = time.time()
        try:
            count = await scan_once(odds_api, tg)
            if count > 0:
                await tg.log(f"📣 Отправлено сигналов: {count}")
        except Exception as e:
            await tg.log(f"❌ Ошибка в цикле: {e}")
        # sleep respecting poll interval
        elapsed = time.time() - started
        to_sleep = max(0, POLL_SECONDS - int(elapsed))
        await asyncio.sleep(to_sleep)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped.")
