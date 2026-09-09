import asyncio


from exchange.nobitex import Nobitex
from exchange.normalizer import ExchangeNormalizer
from database.market_database import MarketDatabase


SYMBOL = "XRPUSDT"
DURATION = 600


async def main():

    bot = Nobitex()
    normalizer = ExchangeNormalizer()

    db = MarketDatabase(
        exchange="nobitex",
        symbol=SYMBOL,
        root=__import__("pathlib").Path.cwd() / "database",
    )

    received = 0
    saved = 0

    print("=" * 70)
    print("KIA BOT - PURE NOBITEX TRADES TEST")
    print("=" * 70)
    print(f"SYMBOL   : {SYMBOL}")
    print(f"DURATION : {DURATION} seconds")
    print("")
    print("CONNECTING...")
    
    await bot.connect()

    # فقط Trades
    await bot.subscribe(
        f"public:trades-{SYMBOL}"
    )

    print("")
    print("CONNECTED")
    print(
        f"SUBSCRIBED: public:trades-{SYMBOL}"
    )
    print("")
    print("RECEIVING TRADES...")
    print("")

    loop = asyncio.get_running_loop()
    start = loop.time()

    try:

        async for message in bot.messages():

            channel = str(
                message.get("channel", "")
            )

            # فقط Trade
            if channel != f"public:trades-{SYMBOL}":
                continue

            received += 1

            normalized = normalizer.normalize(
                message
            )

            db.save(normalized)

            saved += 1

            elapsed = loop.time() - start

            if received == 1 or received % 10 == 0:

                rate = (
                    received / elapsed
                    if elapsed > 0
                    else 0
                )

                print(
                    f"TRADES RECEIVED: {received:6d} | "
                    f"SAVED: {saved:6d} | "
                    f"RATE: {rate:.3f}/sec"
                )

            if elapsed >= DURATION:
                break

    finally:

        await bot.close()

    print("")
    print("=" * 70)
    print("PURE TRADES TEST FINISHED")
    print("=" * 70)
    print(
        f"WEBSOCKET TRADES RECEIVED : {received}"
    )
    print(
        f"DATABASE TRADES SAVED     : {saved}"
    )

    print("")

    if received == saved:
        print(
            "[PASS] "
            "TRADE WEBSOCKET -> NORMALIZER -> DATABASE"
        )
    else:
        print(
            "[FAIL] "
            "TRADE COUNT MISMATCH"
        )

    print("=" * 70)


asyncio.run(main())
