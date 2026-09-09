import asyncio
import sqlite3
from pathlib import Path

from exchange.nobitex import Nobitex
from exchange.normalizer import ExchangeNormalizer
from database.market_database import MarketDatabase


SYMBOL = "XRPUSDT"
DURATION = 600


async def main():

    root = Path.cwd() / "database"

    db = MarketDatabase(
        exchange="nobitex",
        symbol=SYMBOL,
        root=root,
    )

    bot = Nobitex()
    normalizer = ExchangeNormalizer()

    received = 0
    saved = 0

    print("=" * 70)
    print("KIA BOT - NOBITEX TRADE LOAD TEST")
    print("=" * 70)
    print(f"SYMBOL   : {SYMBOL}")
    print(f"DURATION : {DURATION} seconds")
    print("")
    print("CONNECTING...")
    
    await bot.connect()

    await bot.select_market(
        SYMBOL,
        "5",
    )

    print("CONNECTED")
    print("SUBSCRIBED: public:trades-" + SYMBOL)
    print("")
    print("RECEIVING TRADES...")
    print("")

    start = asyncio.get_running_loop().time()

    try:

        async for message in bot.messages():

            channel = str(
                message.get("channel", "")
            )

            if not channel.startswith(
                "public:trades-"
            ):
                continue

            received += 1

            normalized = normalizer.normalize(
                message
            )

            db.save(normalized)

            saved += 1

            if received % 100 == 0:

                elapsed = (
                    asyncio.get_running_loop().time()
                    - start
                )

                rate = (
                    received / elapsed
                    if elapsed > 0
                    else 0
                )

                print(
                    f"TRADES: {received:6d} | "
                    f"SAVED: {saved:6d} | "
                    f"RATE: {rate:.2f}/sec"
                )

            if (
                asyncio.get_running_loop().time()
                - start
                >= DURATION
            ):
                break

    finally:

        await bot.close()

    print("")
    print("=" * 70)
    print("TEST FINISHED")
    print("=" * 70)

    print(f"WEBSOCKET RECEIVED : {received}")
    print(f"DATABASE SAVED     : {saved}")

    trade_db = (
        root
        / "nobitex"
        / SYMBOL
        / f"{SYMBOL}_trades.db"
    )

    connection = sqlite3.connect(
        trade_db
    )

    try:

        cursor = connection.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM trades"
        )

        total = cursor.fetchone()[0]

    finally:

        connection.close()

    print(f"DATABASE TOTAL     : {total}")

    print("")

    if received == saved:
        print("[PASS] WebSocket -> Normalizer -> Database")

    else:
        print("[FAIL] Trade count mismatch")

    print("=" * 70)


asyncio.run(main())
